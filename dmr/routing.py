from collections.abc import Callable, Coroutine, Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar, cast, overload

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.urls import path as _django_path
from django.urls.resolvers import RoutePattern, URLPattern, URLResolver
from django.utils.encoding import force_str
from django.views import defaults
from typing_extensions import override

from dmr.errors import ErrorType, format_error
from dmr.exceptions import InternalServerError, NotAcceptableError
from dmr.openapi.collector import controller_mapping_collector
from dmr.openapi.objects import Components, OpenAPI, Paths

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

    from dmr.internal.types import FormatError
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.renderers import Renderer
    from dmr.serializer import BaseSerializer

_CapturedArgs: TypeAlias = tuple[Any, ...]
_CapturedKwargs: TypeAlias = dict[str, int | str]
_RouteMatch: TypeAlias = tuple[str, _CapturedArgs, _CapturedKwargs]
_AnyPattern: TypeAlias = URLPattern | URLResolver

_SerializerT = TypeVar('_SerializerT', bound='BaseSerializer')


class Router:
    """Collection of HTTP routes for REST framework."""

    __slots__ = ('prefix', 'urls')

    def __init__(self, prefix: str, urls: Sequence[_AnyPattern]) -> None:
        """Just stores the passed routes."""
        self.prefix = prefix
        self.urls = urls

    def get_schema(self, context: 'OpenAPIContext') -> OpenAPI:
        """
        Builds OpenAPI specification.

        This class orchestrates the process of generating a complete OpenAPI
        specification by collecting controllers from the router, generating path
        items for each controller, extracting shared components, and merging
        everything together with the configuration.
        """
        paths_items: Paths = {}

        for path, pattern, controller in controller_mapping_collector(
            self.urls,
            base_path=self.prefix,
        ):
            paths_items[path] = controller.get_path_item(path, pattern, context)

        components = Components(
            schemas=context.registries.schema.schemas,
            security_schemes=context.registries.security_scheme.schemes,
        )
        return context.config_merger(paths_items, components)


# We mimic django's name here:
def build_404_handler(  # noqa: WPS114
    prefix: str,
    /,
    *prefixes: str,
    serializer: type['BaseSerializer'],
    format_error: 'FormatError' = format_error,
    renderers: Sequence['Renderer'] | None = None,
) -> Callable[[HttpRequest, Exception], HttpResponse]:
    """
    Create a 404 handler that returns a response with content negotiation.

    All prefixes are normalized to start with a leading slash.
    If the request path matches any of them, a 404 response is returned
    using the same serializer and renderers as your API.
    If the client's ``Accept`` does not match any renderer, the first
    configured renderer is used.
    For non-matching paths, Django's default ``page_not_found`` handler
    is used.

    Args:
        prefix: Path prefix (e.g. ``'api/'``) for which to return API 404.
        *prefixes: Additional path prefixes.
        format_error: Callable used to build the error body for the response.
        serializer: Serializer class used to serialize the error body.
        renderers: Optional sequence of renderers. If omitted, uses
            :attr:`~dmr.settings.Settings.renderers` from settings.

    See also:
        https://docs.djangoproject.com/en/stable/ref/views/#the-404-page-not-found-view

    """
    from dmr.internal.negotiation import negotiate_renderer  # noqa: PLC0415
    from dmr.response import build_response  # noqa: PLC0415
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    combined = (prefix, *prefixes)
    all_prefixes = tuple(f'/{pref.strip("/")}' for pref in combined)
    renderers_list = (
        resolve_setting(Settings.renderers) if renderers is None else renderers
    )
    renderer_by_type = {
        renderer.content_type: renderer
        for renderer in renderers_list
        if not renderer.streaming
    }
    default_renderer = next(iter(renderer_by_type.values()))

    def factory(
        request: HttpRequest,
        exception: Exception,
    ) -> HttpResponse:
        if not request.path.startswith(all_prefixes):
            return defaults.page_not_found(request, exception)

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
            raw_data=format_error(
                'Page not found',
                error_type=ErrorType.not_found,
            ),
            status_code=HTTPStatus.NOT_FOUND,
            renderer=renderer,
        )

    return factory


# We mimic django's name here:
def build_500_handler(  # noqa: WPS114
    prefix: str,
    /,
    *prefixes: str,
    serializer: type['BaseSerializer'],
    format_error: 'FormatError' = format_error,
    renderers: Sequence['Renderer'] | None = None,
) -> Callable[[HttpRequest], HttpResponse]:
    """
    Create a 500 handler that returns a response with content negotiation.

    All prefixes are normalized to start with a leading slash.
    If the request path matches any of them, a 500 response is returned
    using the same serializer and renderers as your API.
    If the client's ``Accept`` does not match any renderer, the first
    configured renderer is used.
    For non-matching paths, Django's default ``server_error`` handler
    is used.

    Args:
        prefix: Path prefix (e.g. ``'api/'``) for which to return API 500.
        *prefixes: Additional path prefixes.
        format_error: Callable used to build the error body for the response.
        serializer: Serializer class used to serialize the error body.
        renderers: Optional sequence of renderers. If omitted, uses
            :attr:`~dmr.settings.Settings.renderers` from settings.

    See also:
        https://docs.djangoproject.com/en/stable/ref/views/#the-500-server-error-view

    """
    from dmr.internal.negotiation import negotiate_renderer  # noqa: PLC0415
    from dmr.response import build_response  # noqa: PLC0415
    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    combined = (prefix, *prefixes)
    all_prefixes = tuple(f'/{pref.strip("/")}' for pref in combined)
    renderers_list = (
        resolve_setting(Settings.renderers) if renderers is None else renderers
    )
    renderer_by_type = {
        renderer.content_type: renderer
        for renderer in renderers_list
        if not renderer.streaming
    }
    default_renderer = next(iter(renderer_by_type.values()))

    def factory(request: HttpRequest) -> HttpResponse:
        if not request.path.startswith(all_prefixes):
            return defaults.server_error(request)

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
            raw_data=format_error(
                force_str(InternalServerError.default_message),
                error_type=ErrorType.internal_error,
            ),
            status_code=InternalServerError.status_code,
            renderer=renderer,
        )

    return factory


class _PrefixRoutePattern(RoutePattern):
    def __init__(
        self,
        route: str,
        name: str | None = None,
        is_endpoint: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        idx = route.find('<')
        if idx == -1:
            self._prefix = route
            self._is_static = True
        else:
            self._is_static = False
            self._prefix = route[:idx]
        self._is_endpoint = is_endpoint
        super().__init__(route, name, is_endpoint)

    @override
    def match(
        self,
        path: str,
    ) -> _RouteMatch | None:
        if self._is_static:
            if self._is_endpoint and path == self._prefix:
                return '', (), {}
            if not self._is_endpoint and path.startswith(self._prefix):
                return path[len(self._prefix) :], (), {}
        elif path.startswith(self._prefix):
            return super().match(path)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        return None


# NOTE: keep in sync with `django-stubs`!
@overload
def path(
    route: '_StrOrPromise',
    view: Callable[..., HttpResponseBase],
    kwargs: dict[str, Any] | None = None,
    name: str | None = None,
) -> URLPattern: ...
@overload
def path(
    route: '_StrOrPromise',
    view: Callable[..., Coroutine[Any, Any, HttpResponseBase]],
    kwargs: dict[str, Any] | None = None,
    name: str | None = None,
) -> URLPattern: ...
@overload
def path(
    route: '_StrOrPromise',
    view: tuple[Sequence[_AnyPattern], str | None, str | None],
    kwargs: dict[str, Any] | None = None,
    name: str | None = None,
) -> URLResolver: ...
@overload
def path(
    route: '_StrOrPromise',
    view: Sequence[URLResolver | str],
    kwargs: dict[str, Any] | None = None,
    name: str | None = None,
) -> URLResolver: ...


def path(
    route: '_StrOrPromise',
    view: (
        Callable[..., HttpResponseBase]
        | Callable[..., Coroutine[Any, Any, HttpResponseBase]]
        | tuple[Sequence[_AnyPattern], str | None, str | None]
        | Sequence[URLResolver | str]
    ),
    kwargs: dict[str, Any] | None = None,
    name: str | None = None,
) -> _AnyPattern:
    """Creates URL pattern using prefix-based matching for faster routing."""
    return cast(
        _AnyPattern,
        _django_path(  # type: ignore[call-overload]
            route,
            view,
            kwargs,
            name,
            Pattern=_PrefixRoutePattern,
        ),
    )
