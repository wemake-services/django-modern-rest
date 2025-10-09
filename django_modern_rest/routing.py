from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias

from django.http import HttpRequest, HttpResponseBase
from django.urls import URLResolver
from django.views import View
from typing_extensions import override

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller


class Router:
    """Collection of HTTP routes for REST framework."""

    __slots__ = ('urls',)

    def __init__(self, urls: list[URLResolver]) -> None:
        """Just stores the passed routes."""
        self.urls = urls


_ViewFunc: TypeAlias = Callable[..., HttpResponseBase]


def combine_controllers(*controllers: type['Controller']) -> _ViewFunc:
    """Combines several controllers with different http methods into one url."""
    # TODO: validate that there are no intersections of http methods.

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

    return ComposedControllerView.as_view()
