from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponseBase
from django.urls import URLPattern, URLResolver
from django.utils.functional import classproperty
from django.views import View
from typing_extensions import override

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.serialization import BaseSerializer


class Router:
    """Collection of HTTP routes for REST framework."""

    __slots__ = ('urls',)

    def __init__(self, urls: Sequence[URLPattern | URLResolver]) -> None:
        """Just stores the passed routes."""
        self.urls = urls


_SerializerT = TypeVar('_SerializerT', bound='BaseSerializer')
_ViewFunc: TypeAlias = Callable[..., HttpResponseBase]
_ControllerT: TypeAlias = type['Controller[Any]']
_ViewsSpec: TypeAlias = tuple[_ControllerT, _ViewFunc]


def compose_controllers(
    # This seems like a strange design at first, but it actually allows:
    # at least two pos-only controllers and then any amount of extra ones.
    first_controller: type['Controller[_SerializerT]'],
    second_controller: type['Controller[_SerializerT]'],
    /,
    *extra: type['Controller[_SerializerT]'],
) -> type[View]:
    """Combines several controllers with different http methods into one url."""
    controllers = [first_controller, second_controller, *extra]
    is_all_async = _validate_controllers_composition(controllers)

    views = [(controller, controller.as_view()) for controller in controllers]

    method_mapping = _build_method_mapping(views)

    class ComposedControllerView(View):  # noqa: WPS431
        @override
        def dispatch(
            self,
            request: HttpRequest,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponseBase:
            # Routing is efficient in runtime, with O(1) on average.
            # Since we build everything during import time :wink:
            method = request.method.lower()  # type: ignore[union-attr]
            view = method_mapping.get(method)
            if view is not None:
                return view(request, *args, **kwargs)
            return first_controller.handle_method_not_allowed(method)

        @classproperty
        @override
        def view_is_async(cls) -> bool:  # noqa: N805  # pyright: ignore[reportIncompatibleVariableOverride]
            """Returns `True` if all of the controllers are async."""
            return is_all_async

    return ComposedControllerView


def _validate_controllers_composition(
    controllers: list[_ControllerT],
) -> bool:
    # We know that there are at least 2 controllers as this point:
    is_async = bool(controllers[0].view_is_async)
    serializer = controllers[0].serializer

    for controller in controllers:
        if controller.view_is_async is not is_async:
            raise ValueError(
                'Composing controllers with async and sync endpoints '
                'is not supported',
            )
        if serializer is not controller.serializer:
            raise ValueError(
                'Composing controllers with different serializer types '
                'is not supported',
            )

    return is_async


def _build_method_mapping(
    views: list[_ViewsSpec],
) -> Mapping[str, _ViewFunc]:
    method_mapping: dict[str, _ViewFunc] = {}
    for controller, view in views:
        controller_methods = controller.existing_http_methods() - {'options'}
        if not controller_methods:
            raise ValueError(
                f'Controller {controller} must have at least one endpoint '
                'to be composed',
            )
        method_intersection = method_mapping.keys() & controller_methods
        # TODO: decide what to do with default `options` method.
        # Do we need it? Maybe it should be removed?
        if method_intersection:
            raise ValueError(
                f'Controllers have {method_intersection!r} common methods, '
                'while all endpoints must be unique',
            )
        method_mapping.update(dict.fromkeys(controller_methods, view))
    return method_mapping
