import dataclasses
from collections.abc import Mapping, Sequence
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, Final, Protocol

from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

from dmr.errors import ErrorModel, format_error
from dmr.exceptions import NotAcceptableError
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.semantic_schema import AuthProvider

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

    from dmr.controller import Controller
    from dmr.internal.types import FormatError
    from dmr.renderers import Renderer
    from dmr.serializer import BaseSerializer


_CSRF_FAILED_WITH_REASON_MSG: Final = _('CSRF Failed: {reason}')
_CSRF_FAILED_MSG: Final = _('CSRF Failed.')


def csrf_message(reason: str) -> str:
    """
    Return CSRF failure message according the security rules.

    .. versionadded:: 0.16.0
    """
    from django.conf import settings  # noqa: PLC0415

    if settings.DEBUG:
        return _CSRF_FAILED_WITH_REASON_MSG.format(reason=reason)  # type: ignore[no-any-return]

    return force_str(_CSRF_FAILED_MSG)


class _CSRFViewProtocol(Protocol):
    def __call__(
        self,
        request: HttpRequest,
        reason: str = '',
    ) -> HttpResponse: ...


def build_csrf_handler(
    prefix: str,
    /,
    *prefixes: str,
    serializer: type['BaseSerializer'],
    format_error: 'FormatError' = format_error,
    renderers: Sequence['Renderer'] | None = None,
    status_code: HTTPStatus = HTTPStatus.FORBIDDEN,
) -> _CSRFViewProtocol:
    """
    Create a CSRF error handler that returns a response with negotiation.

    Use this function to build ``CSRF_FAILURE_VIEW`` handler in ``settings.py``.

    All prefixes are normalized to start with a leading slash.
    If the request path matches any of them, a REST response is returned
    using the same serializer and renderers as your API.
    If the client's ``Accept`` does not match any renderer, the first
    configured renderer is used.
    For non-matching paths, Django's default ``CSRF_FAILURE_VIEW`` handler
    is used.

    Args:
        prefix: Path prefix (e.g. ``'api/'``) for which to return API responses.
        *prefixes: Additional path prefixes.
        format_error: Callable used to build the error body for the response.
        serializer: Serializer class used to serialize the error body.
        renderers: Optional sequence of renderers. If omitted, uses
            :attr:`~dmr.settings.Settings.renderers` from settings.
        status_code: Status code to be returned. Defaults to ``403``.

    See also:
        https://docs.djangoproject.com/en/6.1/ref/settings/#csrf-failure-view

    .. versionadded:: 0.16.0
    """
    # TODO: unify this logic for all three handlers: 404, 500, this one
    combined = (prefix, *prefixes)
    all_prefixes = tuple(f'/{pref.strip("/")}' for pref in combined)

    def factory(request: HttpRequest, reason: str = '') -> HttpResponse:
        from django.views.csrf import csrf_failure  # noqa: PLC0415

        from dmr.internal.negotiation import negotiate_renderer  # noqa: PLC0415
        from dmr.response import build_response  # noqa: PLC0415
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        if not request.path.startswith(all_prefixes):
            return csrf_failure(request, reason)

        renderers_list = (
            resolve_setting(Settings.renderers)
            if renderers is None
            else renderers
        )
        renderer_by_type = {
            renderer.content_type: renderer
            for renderer in renderers_list
            if not renderer.streaming
        }
        default_renderer = next(iter(renderer_by_type.values()))

        try:
            renderer = negotiate_renderer(
                request,
                renderer_by_type,
                default=default_renderer,
            )
        except NotAcceptableError as exc:
            return build_response(
                serializer=serializer,
                raw_data=format_error(exc),
                status_code=exc.status_code,
                renderer=default_renderer,
            )

        return build_response(
            serializer=serializer,
            raw_data=format_error(csrf_message(reason)),
            status_code=status_code,
            renderer=renderer,
        )

    return factory


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class CsrfResponseSpecProvider(ResponseSpecProvider, AuthProvider):
    """
    Provide response specs for controllers that have ``csrf_exempt = False``.

    Only provides response specs for controllers that set explicit
    ``csrf_exempt = False`` setting and define non-safe HTTP endpoints,
    like ``post`` or ``put``.

    Should be added to :data:`dmr.settings.Settings.semantic_schema_providers`
    setting.

    Attributes:
        error_model: Error model to be returned. Since CSRF is executed
            in a middleware before any controller, we can't get the error
            model from a controller. This is why this has
            to be configured separately.
        status_code: Status code that should be set for failed CSRF responses.
        description: Human readable description, what the response is for.

    .. versionadded:: 0.16.0
    """

    # Instance API:
    error_model: Any = ErrorModel
    status_code: HTTPStatus | None = None
    description: '_StrOrPromise | None' = None

    # Class-level API:
    # Matches Django's definition in `CsrfViewMiddleware`
    _safe_http_methods: ClassVar[frozenset[HTTPMethod]] = frozenset((
        HTTPMethod.GET,
        HTTPMethod.HEAD,
        HTTPMethod.OPTIONS,
        HTTPMethod.TRACE,
    ))

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Returns response specs for CSRF endpoints."""
        if self._is_csrf_disabled(metadata, controller_cls):
            return []

        return self._add_new_response(
            csrf_response_spec(
                controller_cls=None,  # we don't have one at this point yet :(
                status_code=self.status_code,
                description=self.description,
            ),
            existing_responses,
        )

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self._is_csrf_disabled(metadata, controller_cls):
            return {}
        return {}

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        """Provides a security schema usage requirement."""
        if self._is_csrf_disabled(metadata, controller_cls):
            return []
        return [{'csrf': []}]

    def _is_csrf_disabled(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> bool:
        return (
            controller_cls.csrf_exempt
            or metadata.method.upper() in self._safe_http_methods
        )


def csrf_response_spec(
    *,
    controller_cls: type['Controller[BaseSerializer]'] | None,
    status_code: HTTPStatus | None = None,
    description: '_StrOrPromise | None' = None,
) -> ResponseSpec:
    """
    Response spec for CSRF error.

    .. versionadded:: 0.16.0
    """
    return ResponseSpec(
        ErrorModel if controller_cls is None else controller_cls.error_model,
        status_code=(
            HTTPStatus.FORBIDDEN if status_code is None else status_code
        ),
        description=(
            'Raised when CSRF check failed'
            if description is None
            else description
        ),
    )
