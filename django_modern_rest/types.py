from typing import Any, Final, Literal, TypeVar, final, get_args, get_origin

from typing_extensions import get_original_bases


@final
class Empty:
    """Special value for empty defaults."""

    def __bool__(self) -> Literal[False]:
        """Utility for ``if some_object:`` to filter out empty values."""
        return False


#: Default singleton for empty values.
EmptyObj: Final = Empty()


def infer_type_args(
    orig_cls: type[Any],
    given_type: type[Any],
) -> tuple[type[Any], ...]:
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
        if not isinstance(arg, TypeVar)
    )


def infer_bases(
    orig_cls: type[Any],
    given_type: type[Any],
) -> list[type[Any]]:
    """Infers ``__origin_bases__`` from the given type."""
    return [
        base
        for base in get_original_bases(orig_cls)
        if (origin := get_origin(base)) and issubclass(origin, given_type)
    ]
