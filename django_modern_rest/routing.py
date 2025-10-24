from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver
from typing_extensions import override

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.options_mixins import AsyncMetaMixin, MetaMixin
    from django_modern_rest.serialization import BaseSerializer


class Router:
    """Collection of HTTP routes for REST framework."""

    __slots__ = ('urls',)

    def __init__(self, urls: Sequence[URLPattern | URLResolver]) -> None:
        """Just stores the passed routes."""
        self.urls = urls


_SerializerT = TypeVar('_SerializerT', bound='BaseSerializer')
_ViewFunc: TypeAlias = Callable[..., HttpResponse]
_ControllerT: TypeAlias = type['Controller[Any]']


def compose_controllers(
    # This seems like a strange design at first, but it actually allows:
    # at least two pos-only controllers and then any amount of extra ones.
    first_controller: type['Controller[_SerializerT]'],
    second_controller: type['Controller[_SerializerT]'],
    /,
    *extra: type['Controller[_SerializerT]'],
    meta_mixin: type['MetaMixin | AsyncMetaMixin'] | None = None,
    **init_kwargs: Any,
) -> type['Controller[_SerializerT]']:
    """
    Combines several controllers with different http methods into one url.

    Args:
        first_controller: First required controller class to compose.
        second_controller: Second required controller class to compose.
        extra: Other optional controller classes to compose.
        meta_mixin: Type to add to support ``OPTIONS`` method.
        init_kwargs: Kwargs to be passed to controller instance creation.

    Raises:
        ValueError: When local validation fails.
        EndpointMetadataError: When controller validation fails.

    Returns:
        New controller class that has all the endpoints
        from all composed controllers.

    """
    from django_modern_rest.controller import Controller  # noqa: PLC0415

    controllers = [first_controller, second_controller, *extra]
    _validate_controllers_composition(controllers)

    endpoints, method_mapping = _build_method_mapping(controllers)
    serializer = first_controller.serializer
    controller_mixins = (meta_mixin,) if meta_mixin else ()

    class ComposedController(  # noqa: WPS431
        *controller_mixins,  # type: ignore[misc]  # noqa: WPS606
        Controller[serializer],  # type: ignore[valid-type]
    ):
        original_controllers = controllers
        api_endpoints = endpoints

        @override
        def dispatch(
            self,
            request: HttpRequest,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            # Routing is efficient in runtime, with O(1) on average.
            # Since we build everything during import time :wink:
            method = request.method.lower()  # type: ignore[union-attr]
            controller_cls = method_mapping.get(method)
            if controller_cls is not None:
                # Here we have to construct new controller instances,
                # this is rather cheap and has the principle of "least surprise"
                # but I would love to reuse instances for speed :(
                controller = controller_cls(**init_kwargs)
                # We skip useless default checks after `.setup` here:
                controller.setup(request, *args, **kwargs)
                return controller.dispatch(request, *args, **kwargs)
            if meta_mixin and method == 'options':
                return self.api_endpoints['options'](self, *args, **kwargs)
            return first_controller.handle_method_not_allowed(method)

    return ComposedController


def _validate_controllers_composition(
    controllers: list[_ControllerT],
) -> None:
    # We know that there are at least 2 controllers as this point:
    serializer = controllers[0].serializer
    for controller in controllers:
        if serializer is not controller.serializer:
            raise ValueError(
                'Composing controllers with different serializer types '
                'is not supported',
            )


_MethodMappingT: TypeAlias = dict[str, _ControllerT]
_EndpointsT: TypeAlias = dict[str, 'Endpoint']


def _build_method_mapping(
    controllers: list[_ControllerT],
) -> tuple[_EndpointsT, _MethodMappingT]:
    method_mapping: _MethodMappingT = {}
    endpoints: _EndpointsT = {}

    for controller in controllers:
        controller_methods = controller.api_endpoints.keys()
        if not controller_methods:
            raise ValueError(
                f'Controller {controller} must have at least one endpoint '
                'to be composed',
            )
        method_intersection = method_mapping.keys() & controller_methods
        if method_intersection:
            raise ValueError(
                f'Controllers have {method_intersection!r} common methods, '
                'while all endpoints must be unique',
            )

        endpoints.update(controller.api_endpoints)
        method_mapping.update(
            dict.fromkeys(controller.api_endpoints, controller),
        )
    return endpoints, method_mapping
