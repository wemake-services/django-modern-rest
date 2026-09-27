import types as builtin_types
import typing as ty
from collections.abc import Iterator
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Annotated,
    Any,
    Final,
    Protocol,
    TypeAlias,
    TypeVar,
    get_args,
    get_origin,
)

from typing_extensions import TypeAliasType

from dmr.internal.empty import EMPTY as EMPTY

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

    from dmr.errors import ErrorType

    #: Re-export of ``django-stubs`` internal value.
    StrOrPromise: TypeAlias = '_StrOrPromise'
else:
    from django.utils.functional import Promise

    #: Re-export of ``django-stubs`` internal value.
    StrOrPromise: TypeAlias = str | Promise

_MetadataT = TypeVar('_MetadataT')

#: `TypeAliasType` is a different object in `typing` and `typing_extensions`,
#: and `typing` only has it since Python 3.12. We need to know them all.
_TYPE_ALIAS_TYPES: Final = (
    TypeAliasType,
    getattr(ty, 'TypeAliasType', TypeAliasType),
)

#: `X | Y` and `Union[X, Y]` are different objects on older Python versions.
_UNION_TYPES: Final = frozenset((ty.Union, builtin_types.UnionType))

#: How many nested type aliases we are willing to unwrap.
#: Type aliases can be mutually recursive, we don't want to hang on them.
_MAX_ALIAS_DEPTH: Final = 15


def unwrap_type_alias(annotation: Any) -> Any:
    """
    Replaces a type alias with the type it points to.

    Type aliases created with the ``type X = Y`` syntax
    or with ``TypeAliasType`` directly are lazy objects that hide
    the real type behind them, so things like ``Annotated``
    metadata are not visible without unwrapping.

    Aliases of aliases and subscripted generic aliases
    are unwrapped as well. Anything that is not a type alias
    is returned unchanged.

    Raises:
        UnsolvableAnnotationsError: when there are too many nested aliases,
            which also happens for mutually recursive ones.

    """
    from dmr.exceptions import UnsolvableAnnotationsError  # noqa: PLC0415

    for _ in range(_MAX_ALIAS_DEPTH):
        origin = get_origin(annotation)
        if isinstance(annotation, _TYPE_ALIAS_TYPES):
            annotation = annotation.__value__
        elif isinstance(origin, _TYPE_ALIAS_TYPES):
            # Generic aliases keep their args outside of `__value__`,
            # we apply them back to get the real type:
            annotation = origin.__value__[get_args(annotation)]
        else:
            return annotation
    raise UnsolvableAnnotationsError(
        f'Cannot unwrap {annotation!r}, too many nested type aliases',
    )


def iter_union_members(annotation: Any) -> Iterator[Any]:
    """
    Yield union members of *annotation*, unwrapping type aliases.

    When *annotation* is not a union, it is yielded as is.
    """
    annotation = unwrap_type_alias(annotation)
    if get_origin(annotation) in _UNION_TYPES:
        yield from get_args(annotation)
    else:
        yield annotation


def find_annotated_metadata(
    annotation: Any,
    metadata_type: type[_MetadataT],
) -> '_MetadataT | None':
    """
    Return the first *metadata_type* instance in ``Annotated`` metadata.

    Type aliases are unwrapped first, because they hide
    the ``Annotated`` object they point to.
    """
    annotation = unwrap_type_alias(annotation)
    if get_origin(annotation) is not Annotated:
        return None
    for metadata in annotation.__metadata__:
        if isinstance(metadata, metadata_type):
            return metadata
    return None


def has_nested_annotated_metadata(
    annotation: Any,
    metadata_type: type[Any],
) -> bool:
    """
    Whether *metadata_type* is present anywhere inside *annotation*.

    Unlike :func:`find_annotated_metadata`, it also looks
    into unions, generics, and other nested types,
    ``Annotated[Model, metadata] | None``
    or ``list[Annotated[Model, metadata]]`` are found.
    """
    annotation = unwrap_type_alias(annotation)
    if find_annotated_metadata(annotation, metadata_type) is not None:
        return True
    return any(
        has_nested_annotated_metadata(arg, metadata_type)
        for arg in get_args(annotation)
    )


class FormatError(Protocol):
    """Callable that converts an error into a structured Python object."""

    def __call__(
        self,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: 'str | ErrorType | None' = None,
    ) -> Any:
        """Return a formatted representation of the given error."""


def call_init_subclass(from_class: type[Any], cls_arg: type[Any]) -> None:
    """Calls ``__init_subclass__`` from a given class with a *cls_arg*."""
    clsmethod = from_class.__dict__['__init_subclass__']
    clsmethod.__func__(cls_arg)
