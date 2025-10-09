from collections.abc import Iterable
from typing import Any, TypeVar, get_args, get_origin

from typing_extensions import get_original_bases


def infer_type_args(
    orig_cls: type[Any],
    given_type: type[Any],
) -> tuple[type[Any], ...] | None:
    """
    Return type args for the closest given type.

    .. code:: python

        class MyController(Query[MyModel]):
            ...

    Will return ``(MyModel, )`` for ``Query`` as *given_type*.
    """
    needed_bases: Iterable[type[Any]] = [
        base
        for base in get_original_bases(orig_cls)
        if (origin := get_origin(base)) and issubclass(origin, given_type)
    ]
    return tuple(
        arg
        for base_class in needed_bases
        for arg in get_args(base_class)
        if not isinstance(arg, TypeVar)
    )
