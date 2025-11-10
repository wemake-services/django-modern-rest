import dataclasses
from collections.abc import Mapping, Set
from functools import lru_cache
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeVar,
    final,
)

from django.http import HttpResponse

from django_modern_rest.cookies import CookieSpec, NewCookie
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.headers import build_headers
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.response import ResponseSpec
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    MAX_CACHE_SIZE,
    Settings,
    resolve_setting,
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
        if not _is_validation_enabled(
            controller,
            metadata_validate_responses=self.metadata.validate_responses,
        ):
            return response
        schema = self._get_response_schema(response.status_code)
        self._validate_body(response.content, schema, response=response)
        self._validate_response_headers(response, schema)
        self._validate_response_cookies(response, schema)
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
                f'{controller} in {method} returned '
                f'raw data of type {type(structured)} '
                'without associated `@modify` usage.',
            )

        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.modification.status_code,
            headers=build_headers(
                self.metadata.modification,
                self.serializer,
            ),
            cookies=self.metadata.modification.cookies,
        )
        if not _is_validation_enabled(
            controller,
            metadata_validate_responses=self.metadata.validate_responses,
        ):
            return all_response_data
        schema = self._get_response_schema(all_response_data.status_code)
        self._validate_body(structured, schema)
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
        structured: Any | bytes,
        schema: ResponseSpec,
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
            structured = self.serializer.deserialize(structured)

        try:
            self.serializer.from_python(
                structured,
                schema.return_type,
                strict=self.strict_validation,
            )
        except self.serializer.validation_error as exc:
            raise ResponseSerializationError(
                self.serializer.error_serialize(exc),
            ) from None

    def _validate_response_headers(
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response headers against provided metadata."""
        if schema.headers is None:
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

    def _validate_response_cookies(  # noqa: WPS210
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response cookies against provided metadata."""
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
    cookies: Mapping[str, NewCookie | CookieSpec] | None
