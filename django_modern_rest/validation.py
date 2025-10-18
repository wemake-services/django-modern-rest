import dataclasses
from collections import Counter
from collections.abc import Callable, Mapping, Set
from http import HTTPMethod, HTTPStatus
from types import NoneType
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, assert_never, final

from django.http import HttpResponse

from django_modern_rest.exceptions import (
    EndpointMetadataError,
    ResponseSerializationError,
)
from django_modern_rest.headers import (
    HeaderDescription,
    NewHeader,
    build_headers,
)
from django_modern_rest.metadata import (
    EndpointMetadata,
)
from django_modern_rest.response import (
    ResponseDescription,
    ResponseModification,
    infer_status_code,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_VALIDATE_RESPONSES_KEY,
    resolve_setting,
)
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    is_safe_subclass,
    parse_return_annotation,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller

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
        schema = self._get_response_schema(controller, response.status_code)
        self._validate_body(response.content, schema, response=response)
        self._validate_response_object(response, schema)
        return response

    def validate_modification(
        self,
        controller: 'Controller[BaseSerializer]',
        structured: Any,
    ) -> '_ValidationContext':
        """Validate *structured* data before dumping it to json."""
        if self.metadata.modification is None:
            method = self.metadata.method
            raise ResponseSerializationError(
                f'Controller {controller} in {method} returned '
                f'raw data of type {type(structured)} '
                'without associated `@modify` usage.',
            )

        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.modification.status_code,
            headers=build_headers(
                self.metadata.modification.headers,
                self.serializer,
            ),
        )
        if not self._is_validation_enabled(controller):
            return all_response_data
        schema = self._get_response_schema(
            controller,
            all_response_data.status_code,
        )
        self._validate_body(structured, schema)
        return all_response_data

    def _get_response_schema(
        self,
        controller: 'Controller[BaseSerializer]',
        status_code: HTTPStatus | int,
    ) -> ResponseDescription:
        status = HTTPStatus(status_code)
        schema = self.metadata.responses.get(status)
        if schema is not None:
            return schema

        schema = controller.response_map.get(status)
        if schema is not None:
            return schema

        # TODO: support global responses
        allowed = (
            set(self.metadata.responses.keys()) | controller.response_map.keys()
        )
        raise ResponseSerializationError(
            f'Returned {status_code=} is not specified '
            f'in the list of allowed codes {allowed}',
        )

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
            DMR_VALIDATE_RESPONSES_KEY,
        )

    def _validate_body(
        self,
        structured: Any | bytes,
        schema: ResponseDescription,
        *,
        response: HttpResponse | None = None,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Args:
            structured: data to be validated.
            schema: exact response description schema to be a validator.
            response: possible ``HttpResponse`` instance for validation.

        Raises:
            ResponseSerializationError: When validation fails.

        """
        if response:
            structured = self.serializer.from_json(structured)

        try:
            self.serializer.from_python(
                structured,
                schema.return_type,
                strict=self.strict_validation,
            )
        except self.serializer.validation_error as exc:
            raise ResponseSerializationError(
                self.serializer.error_to_json(exc),
            ) from None

    def _validate_response_object(
        self,
        response: HttpResponse,
        schema: ResponseDescription,
    ) -> None:
        """Validates response against provided metadata."""
        # Validate headers, at this point we know
        # that only `HeaderDescription` can be in `metadata.headers`:
        if isinstance(schema.headers, Empty):
            metadata_headers: Set[str] = set()
        else:
            metadata_headers = schema.headers.keys()
            missing_required_headers = {
                header
                for header, response_header in schema.headers.items()
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


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ValidateEndpointPayload:
    """Payload created by ``@validate``."""

    responses: list[ResponseDescription]
    validate_responses: bool | Empty


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModifyEndpointPayload:
    """Payload created by ``@modify``."""

    status_code: HTTPStatus | Empty
    headers: Mapping[str, NewHeader] | Empty
    responses: list[ResponseDescription] | Empty
    validate_responses: bool | Empty


# TODO: possibly split this into several validators? What would API look like?
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadataValidator:  # noqa: WPS214
    """
    Validate ``__endpoint__`` metadata definition.

    It is done during import-time only once, so it can be not blazing fast.
    It is better to be precise here than to be fast.
    """

    payload: ValidateEndpointPayload | ModifyEndpointPayload | None

    def __call__(self, func: Callable[..., Any]) -> EndpointMetadata:
        """Do the validation."""
        return_annotation = parse_return_annotation(func)
        try:
            method = HTTPMethod(func.__name__.upper())
        except ValueError:
            raise EndpointMetadataError(
                f'{func.__name__} is not a valid HTTP method name',
            ) from None
        endpoint = str(func)
        # TODO: validate contoller's defition.
        # Questions: how? when? one time?
        if isinstance(self.payload, ModifyEndpointPayload):
            return self._from_modify(
                self.payload,
                return_annotation,
                method,
                endpoint=endpoint,
            )
        if isinstance(self.payload, ValidateEndpointPayload):
            return self._from_validate(
                self.payload,
                return_annotation,
                method,
                endpoint=endpoint,
            )
        if self.payload is None:
            return self._from_raw_data(
                return_annotation,
                method,
                endpoint=endpoint,
            )
        assert_never(self.payload)

    def _from_validate(
        self,
        payload: ValidateEndpointPayload,
        return_annotation: Any,
        method: HTTPMethod,
        *,
        endpoint: str,
    ) -> EndpointMetadata:
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            needs_response=True,
        )
        self._validate_header_descriptions(payload.responses, endpoint=endpoint)
        self._validate_unique_responses(payload.responses, endpoint=endpoint)
        responses = self._validate_responses(payload, endpoint=endpoint)
        self._validate_http_spec(responses, endpoint=endpoint)
        return EndpointMetadata(
            responses=responses,
            method=method,
            validate_responses=payload.validate_responses,
            modification=None,
        )

    def _from_modify(
        self,
        payload: ModifyEndpointPayload,
        return_annotation: Any,
        method: HTTPMethod,
        *,
        endpoint: str,
    ) -> EndpointMetadata:
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            needs_response=False,
            modify_used=True,
        )
        self._validate_new_headers(payload, endpoint=endpoint)
        if not isinstance(payload.responses, Empty):
            self._validate_header_descriptions(
                payload.responses,
                endpoint=endpoint,
            )
            self._validate_unique_responses(
                payload.responses,
                endpoint=endpoint,
            )
        responses, modification = self._validate_respones_and_modification(
            payload,
            return_annotation,
            method,
            endpoint=endpoint,
        )
        self._validate_http_spec(responses, endpoint=endpoint)
        return EndpointMetadata(
            responses=responses,
            validate_responses=payload.validate_responses,
            method=method,
            modification=modification,
        )

    def _from_raw_data(
        self,
        return_annotation: Any,
        method: HTTPMethod,
        *,
        endpoint: str,
    ) -> EndpointMetadata:
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            needs_response=False,
        )
        status_code = infer_status_code(method)
        modification = ResponseModification(
            return_type=return_annotation,
            status_code=status_code,
            headers=EmptyObj,
        )
        responses = {status_code: modification.to_description()}
        self._validate_http_spec(responses, endpoint=endpoint)
        return EndpointMetadata(
            responses=responses,
            validate_responses=EmptyObj,
            method=method,
            modification=modification,
        )

    def _validate_new_headers(
        self,
        payload: ModifyEndpointPayload,
        *,
        endpoint: str,
    ) -> None:
        if not isinstance(payload.headers, Empty) and any(
            isinstance(header, HeaderDescription)  # pyright: ignore[reportUnnecessaryIsInstance]
            for header in payload.headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns raw data, '
                f'it is not possible to use `HeaderDescription` '
                'because there are no existing headers to describe. Use '
                '`NewHeader` to add new headers to the response',
            )

    def _validate_header_descriptions(
        self,
        responses: list[ResponseDescription],
        *,
        endpoint: str,
    ) -> None:
        for response in responses:
            if isinstance(response.headers, Empty):
                continue
            if any(
                isinstance(header, NewHeader)  # pyright: ignore[reportUnnecessaryIsInstance]
                for header in response.headers.values()
            ):
                raise EndpointMetadataError(
                    f'Cannot use `NewHeader` in {response} , '
                    f'use `HeaderDescription` instead in {endpoint!r}',
                )

    def _validate_return_annotation(
        self,
        return_annotation: Any,
        *,
        endpoint: str,
        needs_response: bool,
        modify_used: bool = False,
    ) -> None:
        if is_safe_subclass(return_annotation, HttpResponse):
            if needs_response:
                return
            part = ' instead of `@modify`' if modify_used else ''
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns HttpResponse, '  # noqa: WPS226
                f'it requires `@validate` decorator{part}',
            )
        if not needs_response:
            return
        raise EndpointMetadataError(
            f'Since {endpoint!r} returns regular data, '
            'it requires `@modify` decorator instead of `@validate`',
        )

    def _validate_http_spec(
        self,
        responses: dict[HTTPStatus, ResponseDescription],
        *,
        endpoint: str,
    ) -> None:
        """Validate that we don't violate HTTP spec."""
        # For status codes < 100 or 204, 304 statuses,
        # no response body is allowed.
        # If you specify a return annotation other than None,
        # an EndpointMetadataError will be raised.
        for status_code, response in responses.items():
            if not is_safe_subclass(response.return_type, NoneType) and (
                status_code < HTTPStatus.CONTINUE
                or status_code
                in {HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED}
            ):
                raise EndpointMetadataError(
                    f'Can only return `None` not {response.return_type} '
                    f'from an endpoint {endpoint!r} '
                    f'with status code {status_code}',
                )
        # TODO: add more checks

    def _validate_unique_responses(
        self,
        responses: list[ResponseDescription],
        *,
        endpoint: str,
    ) -> None:
        counter = Counter(response.status_code for response in responses)
        for status, count in counter.items():
            if count > 1:
                raise EndpointMetadataError(
                    f'Endpoint {endpoint!r} has {status} '
                    f'specified {count} times',
                )

    def _validate_responses(
        self,
        payload: ValidateEndpointPayload,
        *,
        endpoint: str,
    ) -> dict[HTTPStatus, ResponseDescription]:
        # for mypy: this can't happen, we always have at least one response
        # due to `@validate`'s signature.
        assert payload.responses, f'No responses found for {endpoint!r}'  # noqa: S101
        return {resp.status_code: resp for resp in payload.responses}

    def _validate_respones_and_modification(
        self,
        payload: ModifyEndpointPayload,
        return_annotation: Any,
        method: HTTPMethod,
        *,
        endpoint: str,
    ) -> tuple[
        dict[HTTPStatus, ResponseDescription],
        ResponseModification | None,
    ]:
        responses = (
            {}
            if isinstance(payload.responses, Empty)
            else {resp.status_code: resp for resp in payload.responses}
        )
        status_code = (
            infer_status_code(method)
            if isinstance(payload.status_code, Empty)
            else payload.status_code
        )
        modification = ResponseModification(
            return_type=return_annotation,
            headers=payload.headers,
            status_code=status_code,
        )
        if modification.status_code in responses:
            raise EndpointMetadataError(
                f'Do not duplicate {modification.status_code} '
                f'in `responses=` (which are {responses.keys()}), '
                f'it will be added automatically for {endpoint!r}',
            )
        responses[modification.status_code] = modification.to_description()
        return responses, modification


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
    headers: dict[str, str]
