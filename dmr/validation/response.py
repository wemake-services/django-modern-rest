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

from django.http import HttpResponse, HttpResponseBase

from dmr.cookies import NewCookie
from dmr.exceptions import (
    InternalServerError,
    ResponseSchemaError,
    ValidationError,
)
from dmr.headers import build_headers
from dmr.internal.negotiation import (
    media_by_precedence,
    response_validation_negotiator,
)
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.negotiation import (
    get_conditional_types,
    request_renderer,
)
from dmr.serializer import BaseSerializer
from dmr.types import EmptyObj

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.renderers import Renderer

_InputT = TypeVar('_InputT')
_ResponseT = TypeVar('_ResponseT', bound=HttpResponseBase)


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
    from_python_kwargs: ClassVar[Mapping[str, Any]] = {}

    def validate_response(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        response: _ResponseT,
    ) -> _ResponseT:
        """Validate response based on provided schema."""
        if not self.metadata.validate_responses:
            return response
        schema = self._get_response_schema(response.status_code)
        renderer = request_renderer(controller.request)
        parser = response_validation_negotiator(
            controller.request,
            response,
            renderer,
            endpoint.metadata,
        )

        if isinstance(response, HttpResponse):
            # When we have a regular response, we deserialize
            # its content, it is quite clear.
            structured = self.serializer.deserialize(
                response.content,
                parser=parser,
                request=controller.request,
                model=schema.return_type,
            )
        else:
            # But, when we are dealing with `FileResponse`
            # or any other streaming response type,
            # there's nothing really to deserialize.
            # So, we end up working with some specific markers / abstractions.
            structured = self.serializer.deserialize_response(
                response,
                parser=parser,
                request=controller.request,
            )
        self._validate_body(
            structured,
            schema,
            # Here's the tricky part:
            # 1. We first try to use the renderer's default content type
            # 2. But, there might be no renderer yet
            # 3. So, we fallback to the default parser in this case.
            content_type=getattr(renderer, 'content_type', parser.content_type),
        )
        self._validate_response_headers(response, schema)
        self._validate_response_cookies(response, schema)
        self._validate_content_type(response, endpoint.metadata)
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

        allowed = list(map(int, self.metadata.responses.keys()))
        raise ResponseSchemaError(
            f'Returned status code {status_code} is not specified '
            f'in the list of allowed status codes: {allowed!r}',
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
        if (
            schema.limit_to_content_types
            and content_type not in schema.limit_to_content_types
        ):
            hint = list(map(str, schema.limit_to_content_types))
            raise ResponseSchemaError(
                f'Response {schema.status_code} is not allowed '
                f'for {content_type!r}, '
                f'only for {hint!r}',
            )

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
                **self.from_python_kwargs,
            )
        except self.serializer.validation_error as exc:
            raise ValidationError(
                self.serializer.serialize_validation_error(exc),
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            ) from None

    def _validate_response_headers(  # noqa: WPS210
        self,
        response: HttpResponseBase,
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
        response: HttpResponseBase,
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

    def _validate_content_type(
        self,
        response: HttpResponseBase,
        metadata: EndpointMetadata,
    ) -> None:
        """
        We need to be sure that returned response has listed content type.

        Because real endpoints can return a response manually,
        and any content type might be set.
        """
        content_type = response.headers['Content-Type']
        media_types = metadata.renderers.keys()
        for media in media_by_precedence(media_types):
            if media.match(content_type):
                return
        raise ResponseSchemaError(
            f'Response content type {content_type!r} is not '
            f'listed as a possible to be returned {list(media_types)!r}',
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
