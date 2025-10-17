import dataclasses
from collections.abc import Callable, Set
from http import HTTPStatus
from types import NoneType
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, final

from django.http import HttpResponse

from django_modern_rest.exceptions import (
    EndpointMetadataError,
    ResponseSerializationError,
)
from django_modern_rest.headers import (
    HeaderDescription,
    NewHeader,
    ResponseHeadersT,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_VALIDATE_RESPONSE_KEY,
    resolve_setting,
)
from django_modern_rest.types import Empty, is_safe_subclass

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import (
        EndpointMetadata,
        _ExplicitDecoratorNameT,  # pyright: ignore[reportPrivateUsage]
    )

_ResponseT = TypeVar('_ResponseT', bound=HttpResponse)


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseValidator:
    """
    Response validator.

    Can validate responses that return raw data as well as real ``HttpResponse``
    that are returned from endpoints.
    """

    # Public API:
    metadata: 'EndpointMetadata'
    serializer: type[BaseSerializer]
    strict_validation: ClassVar[bool] = True

    def validate_response(
        self,
        controller: 'Controller[BaseSerializer]',
        response: _ResponseT,
    ) -> _ResponseT:
        """Validate ``.content`` of existing ``HttpResponse`` object."""
        if not self._is_validation_enabled(controller):
            return response
        self._validate_body(response.content, response=response)
        self._validate_response_object(response)
        return response

    def validate_content(
        self,
        controller: 'Controller[BaseSerializer]',
        structured: Any,
    ) -> '_ValidationContext':
        """Validate *structured* data before dumping it to json."""
        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.status_code,
            headers=self.metadata.build_headers(self.serializer),
        )
        if not self._is_validation_enabled(controller):
            return all_response_data
        self._validate_body(structured)
        return all_response_data

    def _is_validation_enabled(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> bool:
        """
        Should we run response validation?

        Priority:
        - We first return any directly specified *validate_responses*
          argument to endpoint itself
        - Then we return *validate_responses* from controller if specified
        - Lastly we return the default value from settings
        """
        if isinstance(self.metadata.validate_responses, bool):
            return self.metadata.validate_responses
        if isinstance(controller.validate_responses, bool):
            return controller.validate_responses
        return resolve_setting(  # type: ignore[no-any-return]
            DMR_VALIDATE_RESPONSE_KEY,
        )

    def _validate_body(
        self,
        structured: Any | bytes,
        *,
        response: HttpResponse | None = None,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Args:
            structured: data to be validated.
            response: possible ``HttpResponse`` instance for validation.

        Raises:
            ResponseSerializationError: When validation fails.

        """
        if response:
            structured = self.serializer.from_json(structured)

        try:
            self.serializer.from_python(
                structured,
                self.metadata.return_type,
                strict=self.strict_validation,
            )
        except self.serializer.validation_error as exc:
            raise ResponseSerializationError(
                self.serializer.error_to_json(exc),
            ) from None

    def _validate_response_object(self, response: HttpResponse) -> None:
        """Validates response against provided metadata."""
        # Validate status code:
        if response.status_code != self.metadata.status_code:
            raise ResponseSerializationError(
                f'{response.status_code=} does not match '  # noqa: WPS237
                f'expected {self.metadata.status_code} status code',
            )

        # Validate headers, at this point we know
        # that only `HeaderDescription` can be in `metadata.headers`:
        if isinstance(self.metadata.headers, Empty):
            metadata_headers: Set[str] = set()
        else:
            metadata_headers = self.metadata.headers.keys()
            missing_required_headers = {
                header
                for header, response_header in self.metadata.headers.items()
                if response_header.required
            } - response.headers.keys()
            if missing_required_headers:
                raise ResponseSerializationError(
                    'Response has missing required '
                    f'{missing_required_headers!r} headers',
                )

        extra_response_headers = (
            response.headers.keys()
            - metadata_headers
            - {'Content-Type'}  # it is added automatically
        )
        if extra_response_headers:
            raise ResponseSerializationError(
                'Response has extra undescribed '
                f'{extra_response_headers!r} headers',
            )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadataValidator:
    """
    Validate ``__endpoint__`` metadata definition.

    It is done during import-time only once, so it can be not blazing fast.
    It is better to be precise here than to be fast.
    """

    func: Callable[..., Any]
    explicit_decorator_name: '_ExplicitDecoratorNameT'
    headers: ResponseHeadersT | Empty
    status_code: HTTPStatus
    return_type: Any | Empty

    def __call__(self, return_annotation: Any) -> None:
        """Do the validation."""
        if is_safe_subclass(return_annotation, HttpResponse):
            self._validate_response()
        else:
            self._validate_content()
        self._validate_http_spec()

    def _validate_response(self) -> None:
        if self.explicit_decorator_name in {'modify', None}:
            part = (
                ''
                if self.explicit_decorator_name is None
                else ' instead of `@modify`'
            )
            raise EndpointMetadataError(
                f'Since {self.func!r} returns HttpResponse, '  # noqa: WPS226
                f'it requires `@validate` decorator{part}',
            )

        # Header validation:
        if not isinstance(self.headers, Empty) and any(
            isinstance(header, NewHeader) for header in self.headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {self.func!r} returns HttpResponse, '
                'it is not possible to use `NewHeader`. Use '
                '`.headers = {key: value}` to set headers on response object '
                'and describe them using `HeaderDescription`',
            )

    def _validate_content(self) -> None:
        if self.explicit_decorator_name == 'validate':
            raise EndpointMetadataError(
                f'Since {self.func!r} returns regular data, '
                'it requires `@modify` decorator instead of `@validate`',
            )

        # Header validation:
        if not isinstance(self.headers, Empty) and any(
            isinstance(header, HeaderDescription)
            for header in self.headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {self.func!r} returns raw data, '
                'it is not possible to use `HeaderDescription`, because '
                'there are no existing headers to describe. Use '
                '`NewHeader` to add new headers to the response',
            )

    def _validate_http_spec(self) -> None:
        """Validate that we don't violate HTTP spec."""
        # For status codes < 100 or 204, 304 statuses,
        # no response body is allowed.
        # If you specify a return annotation other than None,
        # an ImproperlyConfiguredException will be raised.
        status_code = self.status_code
        if not is_safe_subclass(self.return_type, NoneType) and (
            status_code < HTTPStatus.CONTINUE
            or status_code in {HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED}
        ):
            raise EndpointMetadataError(
                f'Can only return `None` not {self.return_type} '
                f'from an endpoint with status code {status_code}',
            )
        # TODO: add more checks


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
    headers: dict[str, str]
