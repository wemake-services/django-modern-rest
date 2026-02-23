import types
from collections.abc import Callable, Coroutine, Sequence
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
)
from django.urls import path as _django_path
from django.urls.resolvers import RoutePattern, URLPattern, URLResolver
from django.views.defaults import page_not_found
from typing_extensions import override

from dmr.errors import ErrorType, format_error

if TYPE_CHECKING:
    from dmr.controller import Blueprint, Controller
    from dmr.errors import FormatError
    from dmr.options_mixins import AsyncMetaMixin, MetaMixin
    from dmr.renderers import Renderer
    from dmr.serializer import BaseSerializer

_BlueprintCls: TypeAlias = type['Blueprint[_SerializerT]']
_CapturedArgs: TypeAlias = tuple[Any, ...]
_CapturedKwargs: TypeAlias = dict[str, int | str]
_RouteMatch: TypeAlias = tuple[str, _CapturedArgs, _CapturedKwargs]
_AnyPattern: TypeAlias = URLPattern | URLResolver

_SerializerT = TypeVar('_SerializerT', bound='BaseSerializer')


class Router:
    """Collection of HTTP routes for REST framework."""

    __slots__ = ('urls',)

    def __init__(self, urls: Sequence[_AnyPattern]) -> None:
        """Just stores the passed routes."""
        self.urls = urls


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
    Create a 404 handler that returns an response with content negotiation.

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
        renderer.content_type: renderer for renderer in renderers_list
    }
    default_renderer = next(iter(renderer_by_type.values()))

    def factory(
        request: HttpRequest,
        exception: Exception,
    ) -> HttpResponse:
        if request.path.startswith(all_prefixes):
            renderer = negotiate_renderer(
                request,
                renderer_by_type,
                default=default_renderer,
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
        return page_not_found(request, exception)

    return factory


def compose_blueprints(
    # This seems like a strange design at first, but it actually allows:
    # at least two pos-only controllers and then any amount of extra ones.
    first_blueprint: '_BlueprintCls[_SerializerT]',
    /,
    *extra: '_BlueprintCls[_SerializerT]',
    meta_mixin: type['MetaMixin | AsyncMetaMixin'] | None = None,
) -> type['Controller[_SerializerT]']:
    """
    Combines several blueprints with different http methods into one controller.

    That can be used a single URL route.

    Args:
        first_blueprint: First required blueprint class to compose.
        extra: Other optional blueprint classes to compose.
        meta_mixin: Type to add to support ``OPTIONS`` method.

    Raises:
        EndpointMetadataError: When blueprint validation fails.

    Returns:
        New controller class that has all the endpoints
        from all composed blueprints.

    """
    from dmr.controller import Controller  # noqa: PLC0415

    blueprints = [first_blueprint, *extra]
    type_name = ', '.join(typ.__qualname__ for typ in blueprints)

    serializer = first_blueprint.serializer
    bases = [
        *([meta_mixin] if meta_mixin else []),
        Controller[serializer],  # type: ignore[valid-type]
    ]
    return types.new_class(
        f'Composed@[{type_name}]',
        bases,
        exec_body=_body_builder(blueprints),
    )


def _body_builder(  # :)
    blueprints: list['_BlueprintCls[_SerializerT]'],
) -> Callable[[dict[str, Any]], object]:
    def factory(ns: dict[str, Any]) -> object:
        ns['blueprints'] = blueprints
        return ns

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


@overload
def path(
    route: str,
    view: Callable[..., HttpResponseBase],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLPattern: ...


# NOTE: keep in sync with `django-stubs`!
@overload
def path(
    route: str,
    view: Callable[..., Coroutine[Any, Any, HttpResponseBase]],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLPattern: ...


@overload
def path(
    route: str,
    view: tuple[Sequence[_AnyPattern], str | None, str | None],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLResolver: ...


@overload
def path(
    route: str,
    view: Sequence[URLResolver | str],
    kwargs: dict[str, Any] = ...,
    name: str = ...,
) -> URLResolver: ...


def path(
    route: str,
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
