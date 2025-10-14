from collections.abc import Callable
from typing import Any, Final, final, get_args, get_origin

from typing_extensions import get_original_bases, get_type_hints, override

from django_modern_rest.exceptions import UnsolvableAnnotationsError


@final
class Empty:
    """Special value for empty defaults."""

    @override
    def __repr__(self) -> str:
        """Pretty formatting."""
        return '<empty>'


#: Default singleton for empty values.
EmptyObj: Final = Empty()


def infer_type_args(
    orig_cls: type[Any],
    given_type: type[Any],
) -> tuple[Any, ...]:
    """
    Return type args for the closest given type.

    .. code:: python

        class MyController(Query[MyModel]):
            ...

    Will return ``(MyModel, )`` for ``Query`` as *given_type*.
    """
    return tuple(
        arg
        for base_class in infer_bases(orig_cls, given_type)
        for arg in get_args(base_class)
    )


def infer_bases(
    orig_cls: type[Any],
    given_type: type[Any],
) -> list[Any]:
    """Infers ``__origin_bases__`` from the given type."""
    return [
        base
        for base in get_original_bases(orig_cls)
        if (origin := get_origin(base)) and issubclass(origin, given_type)
    ]


def parse_return_annotation(endpoint_func: Callable[..., Any]) -> Any:
    """
    Parse function annotation and returns the return type.

    Args:
        endpoint_func: function with return type annotation.

    Raises:
        UnsolvableAnnotationsError: when annotation can't be solved.
            Or when does not exist.

    Returns:
        Function's parsed and solved return type.
    """
    try:
        return_annotation = get_type_hints(
            endpoint_func,
        ).get('return', EmptyObj)
    except (TypeError, NameError, ValueError) as exc:
        raise UnsolvableAnnotationsError(
            f'Annotations of {endpoint_func!r} cannot be solved',
        ) from exc

    if return_annotation is EmptyObj:
        raise UnsolvableAnnotationsError(
            f'Function {endpoint_func!r} is missing return type annotation',
        )
    return return_annotation


def is_safe_subclass(annotation: Any, base_class: type[Any]) -> bool:
    """Possibly unwraps subscribbed class before checking for subclassing."""
    # Not a type guard, because `annotation` can be not a `type` :(
    return issubclass(
        get_origin(annotation) or annotation,
        base_class,
    )
