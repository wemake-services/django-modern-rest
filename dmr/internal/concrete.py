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

    It is the subclass that users would write by hand,
    so that concrete views can take their required fields in ``as_view``.
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
    if not given_attrs:
        return None

    existing_serializer = getattr(controller_cls, _SERIALIZER_ATTR, None)
    if _SERIALIZER_ATTR in given_attrs and existing_serializer is not None:
        raise EndpointMetadataError(
            f'{controller_cls!r} already has {existing_serializer!r} '
            'as its serializer, passing `serializer=` would contradict '
            'the type arguments of this controller. '
            'Drop the argument, or pass it to the concrete view instead',
        )

    # The new class is a subclass of *controller_cls* by construction,
    # but type checkers cannot follow `type()` with a type var base:
    return type(  # pyright: ignore[reportReturnType]
        controller_cls.__name__,
        (controller_cls,),
        {
            **given_attrs,
            '__doc__': controller_cls.__doc__,
            '__module__': controller_cls.__module__,
            '__qualname__': controller_cls.__qualname__,
        },
    )
