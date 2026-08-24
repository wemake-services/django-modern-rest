from collections.abc import Callable, Coroutine, Iterable, Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar, cast, overload

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.urls import include
from django.urls import path as _django_path
from django.urls.resolvers import RoutePattern, URLPattern, URLResolver
from django.utils.encoding import force_str
from django.views import defaults
from typing_extensions import override

from dmr.errors import ErrorType, format_error
from dmr.exceptions import InternalServerError, NotAcceptableError
from dmr.internal.routing import RouterMetadata
from dmr.internal.routing import URLExternal as _URLExternal
from dmr.openapi.collector import (
    collect_normalized_paths,
    controller_mapping_collector,
)
from dmr.openapi.objects import PathItem, Paths
from dmr.openapi.openapi import OpenAPI

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
_OpenAPIMetadata: TypeAlias = dict[str, Any]
_ExternalSpec: TypeAlias = tuple[URLPattern, PathItem | None]
_DjangoView: TypeAlias = Callable[
    ...,
    HttpResponseBase | Coroutine[Any, Any, HttpResponseBase],
]

_SerializerT = TypeVar('_SerializerT', bound='BaseSerializer')


class Router:
    """
    Collection of HTTP routes for REST framework.

    Attributes:
        prefix: URL prefix for all routes (e.g., 'api/v1/').
            Defaults to empty string ``''``.
        urls: Sequence of URL patterns and resolvers.
        tags: Optional sequence of tags to group operations in OpenAPI.
            These are merged with endpoint-level tags.
        deprecated: Optional flag to mark all operations as deprecated.
            Combines with endpoint-level deprecated flag using OR logic.

    .. note::

        *tags* and *deprecated* is not applied to external urls'
        metadata. It is always included as-is.

    .. versionchanged:: 0.7.0
        Added *tags* and *deprecated* parameters.

    .. versionchanged:: 0.13.0
        Now you can pass :func:`external_path` objects in *urls*.
        Also accept any :class:`collections.abc.Sequence` as *tags*.
        *urls* parameter is now optional.

    """

    __slots__ = (
        '_path_metadata',
        'deprecated',
        'ignore_from_spec',
        'prefix',
        'tags',
        'urls',
    )

    def __init__(
        self,
        prefix: str = '',
        urls: Iterable[_AnyPattern | _URLExternal] = (),
        *,
        tags: Sequence[str] | None = None,
        deprecated: bool = False,
        ignore_from_spec: bool = False,
    ) -> None:
        """Initialize a router with routes and optional OpenAPI metadata."""
        self.prefix = prefix
        self.urls = self._maybe_process_external(urls)
        self.tags = list(tags or [])
        self.deprecated = deprecated
        self.ignore_from_spec = ignore_from_spec
        # Construct metadata for this new router:
        self._path_metadata: dict[str, RouterMetadata] = {
            new_path: RouterMetadata.from_router(self)
            for _, new_path in collect_normalized_paths(
                self.urls,
                original_prefix='',
                new_prefix=self.prefix,
            )
        }

    def get_schema(self, context: 'OpenAPIContext') -> OpenAPI:  # noqa: WPS231
        """
        Builds OpenAPI specification.

        This class orchestrates the process of generating a complete OpenAPI
        specification by collecting controllers from the router, generating path
        items for each controller, extracting shared components, and merging
        everything together with the configuration.
        """
        paths_items: Paths = {}

        for path, pattern_or_meta, controller in controller_mapping_collector(
            self.urls,
            base_path=self.prefix,
        ):
            if self.metadata_for(path).ignore_from_spec:
                # Skip paths hidden by any router in the inclusion chain:
                continue
            if pattern_or_meta is None:
                # You can also add external views without adding any OpenAPI,
                # this way, it would be hidden from the docs:
                continue
            if isinstance(pattern_or_meta, PathItem):
                # Case for including extrnal views with OpenAPI:
                paths_items[path] = pattern_or_meta
                continue

            # for mypy: it can't narrow down the `tuple` based on the
            # the second item type :/
            assert controller is not None  # noqa: S101
            path_item = controller.get_schema(
                path,
                pattern_or_meta,
                context,
                router=self,
            )
            if path_item is None:
                continue  # It can be private for a reason.
            paths_items[path] = path_item

        return context.config_merger(paths_items, context.get_components())

    def include(
        self,
        router: 'Router',
        *,
        namespace: str | None = None,
        app_name: str | None = None,
    ) -> None:
        """
        Include a router's URLs under a given app name and namespace.

        .. versionadded:: 0.13.0
        """
        self._path_metadata.update({
            new_path: RouterMetadata.from_included(
                self,
                router.metadata_for(original_path),
            )
            for original_path, new_path in collect_normalized_paths(
                router.urls,
                original_prefix=router.prefix,
                new_prefix=self.prefix,
            )
        })

        self.urls.append(
            router.to_urlpatterns(namespace=namespace, app_name=app_name),
        )

    def to_urlpatterns(
        self,
        *,
        namespace: str | None = None,
        app_name: str | None = None,
    ) -> URLResolver:
        """
        Convert router instance into ``urlpatterns`` include API.

        Can be used to include one router into another.
        Or to include a router into the final ``urlpatterns`` list.

        Automatically uses our own faster :func:`path` function.

        .. versionadded:: 0.14.0
        """
        if app_name is None and namespace is not None:
            app_name = namespace

        path_spec = self.urls if app_name is None else (self.urls, app_name)
        return path(self.prefix, include(path_spec, namespace=namespace))

    def metadata_for(self, pattern: str) -> 'RouterMetadata':
        """
        Returns applied nested metadata from all router layers.

        Raises:
            KeyError: if pattern is not found.

        .. versionadded:: 0.15.0
        """
        return self._path_metadata[pattern]

    def _maybe_process_external(
        self,
        urls: Iterable[_AnyPattern | _URLExternal],
    ) -> list[_AnyPattern]:
        django_like_urls: list[_AnyPattern] = []
        for url in urls:
            if isinstance(url, _URLExternal):
                django_like_urls.append(url.get_url_with_metadata())
            else:
                django_like_urls.append(url)
        return django_like_urls


def external_path(
    route: '_StrOrPromise',
    view: _DjangoView,
    *,
    openapi: PathItem | None,
    kwargs: dict[str, Any] | None = None,
    name: str | None = None,
) -> '_URLExternal':
    """
    Add an external path onto the DMR routing system.

    Automatically uses our own faster :func:`path` function.

    Parameters:
        route: String route for the view.
        view: Function or class view, supports both sync and async callables.
        openapi: OpenAPI metadata to show in the spec.
            Or ``None`` to hide this endpoint.
        kwargs: Init kwargs for the view.
        name: Name to resolve this URL.

    .. important::

        This function only works when including
        a URL into our own :class:`Router` objects,
        not into the Django own ``urlpatterns``.

        Django check ``urls.E004`` covers this statically.

    See :ref:`external-views` for more info.

    .. versionadded:: 0.13.0
    """
    return _URLExternal(
        path(route, view, kwargs=kwargs, name=name),
        openapi=openapi,
    )


# We mimic django's name here:
def build_404_handler(
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
def build_500_handler(
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
    view: _DjangoView,
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
        _DjangoView
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
