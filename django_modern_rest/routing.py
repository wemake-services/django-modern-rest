from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias

from django.http import HttpRequest, HttpResponseBase
from django.urls import URLPattern, URLResolver
from django.utils.functional import classproperty
from django.views import View
from typing_extensions import override

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Router:
    """Collection of HTTP routes for REST framework."""

    __slots__ = ('urls',)

    def __init__(self, urls: Sequence[URLPattern | URLResolver]) -> None:
        """Just stores the passed routes."""
        self.urls = urls


_ViewFunc: TypeAlias = Callable[..., HttpResponseBase]


def compose_controllers(*controllers: type['Controller[Any]']) -> type[View]:
    """Combines several controllers with different http methods into one url."""
    # TODO: validate that there are no intersections of http methods.
    # TODO: validate that all controllers are either sync or async
    # TODO: validate that there's at least one controller

    views = [(controller, controller.as_view()) for controller in controllers]

    class ComposedControllerView(View):  # noqa: WPS431
        @override
        def dispatch(
            self,
            request: HttpRequest,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponseBase:
            method = request.method.lower()  # type: ignore[union-attr]
            for controller, view_func in views:
                if method in controller.existing_http_methods:
                    return view_func(request, *args, **kwargs)
            return self.http_method_not_allowed(request, *args, **kwargs)

        @override
        @classproperty
        def view_is_async(cls) -> bool:  # noqa: N805
            """Returns `True` if all of the controllers are async."""
            return all(controller.view_is_async for controller, _ in views)

    return ComposedControllerView
