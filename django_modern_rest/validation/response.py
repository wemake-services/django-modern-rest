import dataclasses
from collections.abc import Mapping
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeVar,
    final,
)

from django.http import HttpResponse

from django_modern_rest.cookies import NewCookie
from django_modern_rest.exceptions import (
    InternalServerError,
    ResponseSchemaError,
    ValidationError,
)
from django_modern_rest.headers import build_headers
from django_modern_rest.internal.negotiation import (
    response_validation_negotiator,
)
from django_modern_rest.metadata import EndpointMetadata, ResponseSpec
from django_modern_rest.negotiation import (
    get_conditional_types,
    request_renderer,
)
from django_modern_rest.serializer import BaseSerializer
from django_modern_rest.types import EmptyObj

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.renderers import Renderer

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

    # Public class-level API:
    strict_validation: ClassVar[bool] = True

    def validate_response(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        response: _ResponseT,
    ) -> _ResponseT:
        """Validate ``.content`` of existing ``HttpResponse`` object."""
        if not self.metadata.validate_responses:
            return response
        schema = self._get_response_schema(response.status_code)
        parser = response_validation_negotiator(
            controller.request,
            response,
            request_renderer(controller.request),
            endpoint.metadata,
        )

        structured = self.serializer.deserialize(
            response.content,
            parser=parser,
            request=controller.request,
        )
        self._validate_body(
            structured,
            schema,
            content_type=parser.content_type,
        )
        self._validate_response_headers(response, schema)
        self._validate_response_cookies(response, schema)
        return response

    def validate_modification(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        structured: Any,
    ) -> '_ValidationContext':
        """Validate *structured* data before dumping it to json."""
        if self.metadata.modification is None:
            # Happens in cases when `@validate` returns raw data:
            method = self.metadata.method
            raise InternalServerError(
                f'{type(controller)!r} in {method!r} returned '
                f'raw data of type {type(structured)!r} '
                'without associated `@modify` usage.',
            )

        renderer = request_renderer(controller.request)
        # Renderer is present at this point, 100%
        assert renderer is not None  # noqa: S101
        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.modification.status_code,
            headers=build_headers(
                self.metadata.modification,
                renderer,
            ),
            cookies=self.metadata.modification.actionable_cookies(),
            renderer=renderer,
        )
        if not self.metadata.validate_responses:
            return all_response_data
        schema = self._get_response_schema(all_response_data.status_code)
        self._validate_body(
            structured,
            schema,
            content_type=renderer.content_type,
        )
        return all_response_data

    def _get_response_schema(
        self,
        status_code: HTTPStatus | int,
    ) -> ResponseSpec:
        status = HTTPStatus(status_code)
        schema = self.metadata.responses.get(status)
        if schema is not None:
            return schema

        allowed = set(self.metadata.responses.keys())
        raise ResponseSchemaError(
            f'Returned {status_code=} is not specified '
            f'in the list of allowed codes {allowed!r}',
        )

    def _validate_body(
        self,
        structured: Any,
        schema: ResponseSpec,
        *,
        content_type: str,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Args:
            structured: data to be validated.
            schema: exact response description schema to be a validator.
            content_type: content type that is used for this body.

        Raises:
            ResponseSchemaError: When validation fails.

        """
        content_types = get_conditional_types(schema.return_type)
        if content_types:
            model = content_types.get(content_type, EmptyObj)
            if model is EmptyObj:
                hint = [str(ct) for ct in content_types]
                raise ResponseSchemaError(
                    f'Content-Type {content_type!r} is not '
                    f'listed in supported content types {hint!r}',
                )
        else:
            model = schema.return_type

        try:
            self.serializer.from_python(
                structured,
                model,
                strict=self.strict_validation,
            )
        except self.serializer.validation_error as exc:
            raise ValidationError(
                self.serializer.serialize_validation_error(exc),
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            ) from None

    def _validate_response_headers(  # noqa: WPS210
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response headers against provided metadata."""
        response_headers = {header.lower() for header in response.headers}
        metadata_headers = {
            header.lower()
            for header, response_header in (schema.headers or {}).items()
            if not response_header.schema_only
        }
        if schema.headers is not None:
            missing_required_headers = {
                header.lower()
                for header, response_header in schema.headers.items()
                if response_header.required and not response_header.schema_only
            } - response_headers
            if missing_required_headers:
                raise ResponseSchemaError(
                    'Response has missing required '
                    f'{missing_required_headers!r} headers',
                )

        extra_response_headers = (
            response_headers
            - metadata_headers
            - {'content-type'}  # it is added automatically
        )
        if extra_response_headers:
            raise ResponseSchemaError(
                'Response has extra real undescribed '
                f'{extra_response_headers!r} headers',
            )

    def _validate_response_cookies(  # noqa: WPS210
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response cookies against provided metadata."""
        # NOTE: unlike http headers, cookies are case sensitive.
        metadata_cookies = schema.cookies or {}

        # Find missing cookies:
        missing_required_cookies = {
            cookie
            for cookie, response_cookie in metadata_cookies.items()
            if response_cookie.required and not response_cookie.schema_only
        } - response.cookies.keys()
        if missing_required_cookies:
            raise ResponseSchemaError(
                'Response has missing required '
                f'{missing_required_cookies!r} cookie',
            )

        # Find extra cookies:
        extra_response_cookies = response.cookies.keys() - {
            cookie
            for cookie, response_cookie in metadata_cookies.items()
            if not response_cookie.schema_only
        }
        if extra_response_cookies:
            raise ResponseSchemaError(
                'Response has extra real undescribed '
                f'{extra_response_cookies!r} cookies',
            )

        # Find not fully described cookies:
        for cookie_key, cookie_body in response.cookies.items():
            if not metadata_cookies[cookie_key].is_equal(cookie_body):
                raise ResponseSchemaError(
                    f'Response cookie {cookie_key}={cookie_body!r} is not '
                    f'equal to {metadata_cookies[cookie_key]!r}',
                )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
    headers: dict[str, str]
    cookies: Mapping[str, NewCookie] | None
    renderer: 'Renderer'
