import dataclasses
from collections.abc import Callable, Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeAlias, cast

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


DumpedSchema: TypeAlias = dict[str, Any]
_ConverterFunc: TypeAlias = Callable[['DataclassInstance'], DumpedSchema]
_NormalizeKeyFunc: TypeAlias = Callable[[str], str]
_NormalizeValueFunc: TypeAlias = Callable[[Any, _ConverterFunc], Any]


def dump_schema(to_convert: 'DataclassInstance') -> DumpedSchema:  # noqa: WPS231
    """Converts any dataclass object into a JSON schema."""
    schema: DumpedSchema = {}

    for field in dataclasses.fields(to_convert):
        schema_value = getattr(to_convert, field.name, None)
        if field.name.startswith('_') or schema_value is None:
            continue
        if field.name == 'required' and not schema_value:
            continue  # Skip empty `required` field

        schema[_dump_field(field.name, field.metadata)] = _dump_value(
            schema_value,
        )

    return schema


def _dump_field(key: str, metadata: Mapping[Any, Any]) -> str:
    """
    Convert a Python field name to an OpenAPI-compliant key.

    This function handles the conversion from Python naming conventions
    (snake_case) to OpenAPI naming conventions (camelCase) with special
    handling for reserved keywords and common patterns.

    Args:
        key: The Python field name to normalize.
        metadata: Metadata from the dataclass field if it is defined.

    Returns:
        The normalized key suitable for OpenAPI specification

    """
    alias = metadata.get('alias')
    if alias:
        assert isinstance(alias, str), alias  # noqa: S101
        return alias

    if '_' in key:
        components = key.split('_')
        return components[0].lower() + ''.join(
            component.title() for component in components[1:]
        )
    return key


# pyright: reportUnknownVariableType=false
def _dump_value(to_normalize: Any) -> Any:
    """
    Normalize a value for OpenAPI schema.

    Handles:

    - Dataclass instances (convert to dict)
    - Lists (process elements recursively)
    - Dicts (process keys and values recursively)
    - Primitive values (return as-is)
    - Enums (value is returned)

    """
    if dataclasses.is_dataclass(to_normalize):
        return dump_schema(cast('DataclassInstance', to_normalize))

    if isinstance(to_normalize, list):
        return [_dump_value(list_item) for list_item in to_normalize]

    if isinstance(to_normalize, dict):
        return {
            _dump_value(dict_key): _dump_value(dict_val)
            for dict_key, dict_val in to_normalize.items()
        }

    if isinstance(to_normalize, Enum):
        return to_normalize.value

    return to_normalize
