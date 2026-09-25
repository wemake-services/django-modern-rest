import types
from typing import TYPE_CHECKING, Any, Final, TypeVar

from dmr.exceptions import EndpointMetadataError

if TYPE_CHECKING:
    from dmr.controller import Controller

_ControllerT = TypeVar('_ControllerT', bound='Controller[Any]')

#: Name of the attribute that holds the serializer type of a controller.
_SERIALIZER_ATTR: Final = 'serializer'


def build_concrete_controller(
    controller_cls: type[_ControllerT],
    **class_attrs: object,
) -> type[_ControllerT] | None:
    """
    Subclass *controller_cls* with the given class attributes.

    It is the subclass that users would write by hand:
    ``serializer`` is passed as a type argument of the base,
    everything else becomes a class attribute.
    Arguments that are ``None`` were not given and are skipped.

    Returns:
        The new subclass, or ``None`` when there is nothing to set,
        which means that *controller_cls* must be routed as-is.

    Raises:
        EndpointMetadataError: When ``serializer`` is given
            to a controller that already has an exact one,
            since the two would disagree.

    """
    given_attrs = {
        attr_name: attr_value
        for attr_name, attr_value in class_attrs.items()
        if attr_value is not None
    }
    serializer = given_attrs.pop(_SERIALIZER_ATTR, None)
    if serializer is None and not given_attrs:
        return None

    return types.new_class(
        controller_cls.__name__,
        (_parametrized_base(controller_cls, serializer),),
        # Otherwise it would be `types`, where the class is created:
        exec_body=lambda namespace: namespace.update(
            given_attrs,
            __module__=controller_cls.__module__,
        ),
    )


def _parametrized_base(
    controller_cls: type[_ControllerT],
    serializer: object,
) -> object:
    """
    Return the base to subclass, with *serializer* as its type argument.

    Raises:
        EndpointMetadataError: When *controller_cls*
            already has an exact serializer.

    """
    if serializer is None:
        return controller_cls

    existing_serializer = getattr(controller_cls, _SERIALIZER_ATTR, None)
    if existing_serializer is not None:
        raise EndpointMetadataError(
            f'{controller_cls!r} already has {existing_serializer!r} '
            'as its serializer, passing `serializer=` would contradict '
            'the type arguments of this controller. '
            'Drop the argument, or pass it to the concrete view instead',
        )
    return controller_cls[serializer]  # type: ignore[index]
