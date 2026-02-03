import dataclasses
from collections.abc import Mapping
from functools import lru_cache
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    TypeVar,
    final,
    get_origin,
)

from django.http import HttpResponse

from django_modern_rest.cookies import NewCookie
from django_modern_rest.envs import MAX_CACHE_SIZE
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.headers import build_headers
from django_modern_rest.internal.negotiation import ConditionalType
from django_modern_rest.metadata import EndpointMetadata, ResponseSpec
from django_modern_rest.negotiation import response_validation_negotiator
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import Settings, resolve_setting

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
        if not _is_validation_enabled(
            controller,
            metadata_validate_responses=self.metadata.validate_responses,
        ):
            return response
        schema = self._get_response_schema(response.status_code)
        parser_cls = response_validation_negotiator(
            controller.request,
            response,
            endpoint.metadata,
        )

        structured = self.serializer.deserialize(
            response.content,
            parser_cls=parser_cls,
        )
        self._validate_body(
            structured,
            schema,
            content_type=parser_cls.content_type,
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
            method = self.metadata.method
            raise ResponseSerializationError(
                f'{controller} in {method} returned '
                f'raw data of type {type(structured)} '
                'without associated `@modify` usage.',
            )

        renderer_class = endpoint.response_negotiator(controller.request)
        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.modification.status_code,
            headers=build_headers(
                self.metadata.modification,
                renderer_class,
            ),
            cookies=self.metadata.modification.cookies,
            renderer_cls=renderer_class,
        )
        if not _is_validation_enabled(
            controller,
            metadata_validate_responses=self.metadata.validate_responses,
        ):
            return all_response_data
        schema = self._get_response_schema(all_response_data.status_code)
        self._validate_body(
            structured,
            schema,
            content_type=renderer_class.content_type,
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
        raise ResponseSerializationError(
            f'Returned {status_code=} is not specified '
            f'in the list of allowed codes {allowed}',
        )

    def _validate_body(
        self,
        structured: Any,
        schema: ResponseSpec,
        *,
        content_type: str | None = None,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Args:
            structured: data to be validated.
            schema: exact response description schema to be a validator.
            content_type: content type that is used for this body.

        Raises:
            ResponseSerializationError: When validation fails.

        """
        if (
            content_type
            and get_origin(schema.return_type) is Annotated
            and schema.return_type.__metadata__
            and isinstance(
                schema.return_type.__metadata__[0],
                ConditionalType,
            )
        ):
            content_types = schema.return_type.__metadata__[0].computed
            if content_type not in content_types:
                raise ResponseSerializationError(
                    self.serializer.error_serialize(
                        f'Content-Type {content_type} is not '
                        f'listed in {content_types=}',
                    ),
                )
            model = content_types[content_type]
        else:
            model = schema.return_type

        try:
            self.serializer.from_python(
                structured,
                model,
                strict=self.strict_validation,
            )
        except self.serializer.validation_error as exc:
            raise ResponseSerializationError(
                self.serializer.error_serialize(exc),
            ) from None

    def _validate_response_headers(  # noqa: WPS210
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response headers against provided metadata."""
        response_headers = {header.lower() for header in response.headers}
        metadata_headers = {header.lower() for header in (schema.headers or ())}
        if schema.headers is not None:
            missing_required_headers = {
                header.lower()
                for header, response_header in schema.headers.items()
                if response_header.required
            } - response_headers
            if missing_required_headers:
                raise ResponseSerializationError(
                    'Response has missing required '
                    f'{missing_required_headers!r} headers',
                )

        extra_response_headers = (
            response_headers
            - metadata_headers
            - {'content-type'}  # it is added automatically
        )
        if extra_response_headers:
            raise ResponseSerializationError(
                'Response has extra undescribed '
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
            if response_cookie.required
        } - response.cookies.keys()
        if missing_required_cookies:
            raise ResponseSerializationError(
                'Response has missing required '
                f'{missing_required_cookies!r} cookie',
            )

        # Find extra cookies:
        extra_response_cookies = (
            response.cookies.keys() - metadata_cookies.keys()
        )
        if extra_response_cookies:
            raise ResponseSerializationError(
                'Response has extra undescribed '
                f'{extra_response_cookies!r} cookies',
            )

        # Find not fully described cookies:
        for cookie_key, cookie_body in response.cookies.items():
            if not metadata_cookies[cookie_key].is_equal(cookie_body):
                raise ResponseSerializationError(
                    f'Response cookie {cookie_key}={cookie_body!r} is not '
                    f'equal to {metadata_cookies[cookie_key]!r}',
                )


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _is_validation_enabled(
    controller: 'Controller[BaseSerializer]',
    *,
    metadata_validate_responses: bool | None,
) -> bool:
    """
    Should we run response validation?

    Priority:
    - We first return any directly specified *validate_responses*
        argument to endpoint itself
    - Second is *validate_responses* on the blueprint, if it exists
    - Then we return *validate_responses* from controller if specified
    - Lastly we return the default value from settings
    """
    if metadata_validate_responses is not None:
        return metadata_validate_responses
    if (
        controller.blueprint
        and controller.blueprint.validate_responses is not None
    ):
        return controller.blueprint.validate_responses
    if controller.validate_responses is not None:
        return controller.validate_responses
    return resolve_setting(  # type: ignore[no-any-return]
        Settings.validate_responses,
    )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
    headers: dict[str, str]
    cookies: Mapping[str, NewCookie] | None
    renderer_cls: type['Renderer']
