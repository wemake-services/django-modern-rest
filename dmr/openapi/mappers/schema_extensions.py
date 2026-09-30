# pyright: reportUnknownVariableType=false

import dataclasses
import functools
from types import UnionType
from typing import Any, Final, Union, get_args, get_origin, get_type_hints

from dmr.openapi.mappers.schema_normalization import dump_field

#: Name of the field that holds specification extensions on OpenAPI objects.
EXTENSIONS_FIELD: Final = 'x_extensions'

#: The same field as ``pydantic`` expects it, when loading a raw schema.
_EXTENSIONS_KEY: Final = dump_field(EXTENSIONS_FIELD, None)
_UNION_ORIGINS: Final = (Union, UnionType)


def nest_extensions(raw: Any, annotation: Any) -> Any:
    """
    Move ``x-`` keys of *raw* into ``x_extensions`` of the matching object.

    ``pydantic`` ignores unknown keys, so specification extensions
    would be lost otherwise. The walk is type-directed: only positions
    typed as an object with ``x_extensions`` are changed,
    map positions like ``Schema.properties`` keep ``x-`` keys as they are.
    Positions without type information (``None``) are kept as they are.

    .. versionadded:: 0.16.0
    """
    if annotation is None:
        return raw
    if isinstance(raw, list):
        item_type = _generic_arg(annotation, list, index=0)
        return [nest_extensions(list_item, item_type) for list_item in raw]
    if not isinstance(raw, dict):
        return raw

    model = _pick_dataclass(annotation, raw)  # pyright: ignore[reportUnknownArgumentType]
    if model is not None:
        return _nest_object(raw, model)  # pyright: ignore[reportUnknownArgumentType]

    value_type = _generic_arg(annotation, dict, index=1)
    return {
        dict_key: nest_extensions(dict_val, value_type)
        for dict_key, dict_val in raw.items()
    }


def _nest_object(
    raw: dict[str, Any],
    model: Any,  # a dataclass type, see `_field_hints`
) -> dict[str, Any]:
    field_hints = _field_hints(model)
    nested: dict[str, Any] = {}
    extensions: dict[str, Any] = {}
    for raw_key, raw_value in raw.items():
        if _EXTENSIONS_KEY in field_hints and raw_key.startswith('x-'):
            extensions[raw_key] = raw_value
        else:
            # Unknown keys have no hint, `pydantic` reports them later:
            nested[raw_key] = nest_extensions(
                raw_value,
                field_hints.get(raw_key),
            )
    if extensions:
        nested[_EXTENSIONS_KEY] = extensions
    return nested


@functools.cache
def _field_hints(model: Any) -> dict[str, Any]:
    """Map dumped OpenAPI keys of *model* to its resolved field types."""
    # *model* is a dataclass type, `type[Any]` is not `Hashable` for mypy.
    # Objects use forward references to each other, this namespace
    # resolves them. Must be lazy to avoid circular imports:
    from dmr.openapi import objects  # noqa: PLC0415

    hints = get_type_hints(model, localns=objects.__dict__)
    return {
        dump_field(field.name, field.type): hints[field.name]
        for field in dataclasses.fields(model)
    }


def _union_members(annotation: Any) -> tuple[Any, ...]:
    if get_origin(annotation) in _UNION_ORIGINS:
        return get_args(annotation)
    return (annotation,)


def _pick_dataclass(annotation: Any, raw: dict[str, Any]) -> type[Any] | None:
    """Choose which dataclass of a union describes *raw*, if any."""
    candidates = [
        member
        for member in _union_members(annotation)
        if isinstance(member, type) and dataclasses.is_dataclass(member)
    ]
    # `Reference` never has extensions, so it is only picked by its `$ref`:
    references = [
        member for member in candidates if member.__name__ == 'Reference'
    ]
    if references and '$ref' in raw:
        return references[0]
    others = [member for member in candidates if member not in references]
    return others[0] if others else None


def _generic_arg(annotation: Any, origin: type[Any], *, index: int) -> Any:
    """Find the type argument of a ``list`` or ``dict`` member of a union."""
    for member in _union_members(annotation):
        if get_origin(member) is origin:
            return get_args(member)[index]
    return None
