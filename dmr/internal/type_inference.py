from typing import Any, TypeVar, get_args

from typing_extensions import NoDefault


def resolve_type_args(base: Any) -> tuple[Any, ...]:
    """
    Returns type args of a base class with :pep:`696` defaults applied.

    Subscripted bases already have their type var defaults
    filled in by the runtime: ``Base[int]`` is ``Base[int, str]``
    for ``class Base(Generic[_FirstT, _SecondT = str])``.

    But, bare bases like ``class Sub(Base): ...``
    don't have any type args in runtime at all.
    Type-checkers do use type var defaults there, so we do the same.
    """
    type_args = get_args(base)
    if type_args:
        return type_args

    type_params = getattr(base, '__parameters__', ())
    type_defaults = tuple(map(resolve_type_var_default, type_params))
    if type_defaults == type_params:
        # Without any defaults there's nothing to infer from a bare base:
        # we don't want to treat `class Sub(Base)` as `Base[_FirstT]`.
        return ()
    return type_defaults


def resolve_type_var_default(type_var: TypeVar) -> Any:
    """
    Returns the :pep:`696` default of a type var or the type var itself.

    Type vars only have defaults when they are created
    with ``typing_extensions.TypeVar``
    or with :class:`typing.TypeVar` on Python 3.13 and above.

    Defaults can be type vars themselves,
    they are not resolved any further here.
    """
    default = getattr(type_var, '__default__', NoDefault)
    if default is NoDefault:
        return type_var
    return default
