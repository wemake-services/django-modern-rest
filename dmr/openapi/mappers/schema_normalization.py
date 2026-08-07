import dataclasses
import re
import typing
from collections.abc import Callable, Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any, Final, TypeAlias, TypeVar, cast

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from dmr.serializer import BaseSerializer


DumpedSchema: TypeAlias = dict[str, Any]
_ConverterFunc: TypeAlias = Callable[['DataclassInstance'], DumpedSchema]
_NormalizeKeyFunc: TypeAlias = Callable[[str], str]
_NormalizeValueFunc: TypeAlias = Callable[[Any, _ConverterFunc], Any]


def dump_schema(to_convert: 'DataclassInstance') -> DumpedSchema:  # noqa: WPS231
    """
    Converts any dataclass object into a JSON schema.

    .. versionchanged:: 0.13.0
        It used to be named ``dmr.openapi.objects.openapi.convert``.

    """
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


_ThingT = TypeVar('_ThingT', bound='DataclassInstance')


def load_schema(
    unstructured: dict[str, Any],
    model: type[_ThingT],
    serializer: type['BaseSerializer'],
) -> _ThingT:
    """
    Load *unstructured* schema into the *model* dataclass type.

    Used to include external schemas into the project.

    .. versionadded:: 0.13.0
    """
    from dmr.openapi import objects  # noqa: PLC0415

    updated = {}
    for key, schema_value in unstructured.items():
        updated[_load_field(key, model)] = _load_value(key, schema_value, model)

    return serializer.from_python(
        updated,
        model=model,
        strict=False,
        extra_namespace=objects.__dict__,
    )


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


_FIRST_CAP_RE: Final = re.compile(r'(.)([A-Z][a-z]+)')
_ALL_CAP_RE: Final = re.compile(r'([a-z0-9])([A-Z])')
_REPLACEMENT_STR: Final = r'\1_\2'


def _load_field(
    key: str,
    model: type['DataclassInstance'],
) -> str:
    """
    Convert an OpenAPI key to the form pydantic expects for *model*.

    Pydantic uses field aliases for aliased fields and Python field
    names (snake_case) for non-aliased fields.  This function:

    - Returns the key unchanged when it matches a field alias
      (e.g. ``$ref``, ``not``, ``$dynamicRef``).
    - Converts camelCase to snake_case otherwise
      (e.g. ``allOf`` → ``all_of``).

    """
    for dc_field in dataclasses.fields(model):
        if dc_field.metadata.get('alias') == key:
            return key
    return _ALL_CAP_RE.sub(
        _REPLACEMENT_STR,
        _FIRST_CAP_RE.sub(_REPLACEMENT_STR, key),
    ).lower()


def _load_value(  # noqa: WPS231
    key: str,
    schema_value: Any,
    model: type['DataclassInstance'],
) -> Any:
    """
    Recursively normalize a schema value for loading into a dataclass.

    Handles:

    - Dict fields of type ``dict[str, X]``: normalizes values, preserves keys
    - Nested schema object dicts: normalizes camelCase and ``$``-alias keys
    - Lists: recursively normalizes each item
    - Primitives: returned as-is

    """
    if isinstance(schema_value, dict):
        if _is_dict_field(key, model):
            return {k: _normalize_nested(v) for k, v in schema_value.items()}
        return _normalize_nested_dict(schema_value)
    if isinstance(schema_value, list):
        return [_normalize_nested(item) for item in schema_value]
    return schema_value


def _is_dict_field(key: str, model: type['DataclassInstance']) -> bool:
    """Return ``True`` if *key* resolves to a ``dict[...]`` field in *model*."""
    from dmr.openapi import objects  # noqa: PLC0415

    # Resolve alias to Python field name
    python_key = key
    for dc_field in dataclasses.fields(model):
        if dc_field.metadata.get('alias') == key:
            python_key = dc_field.name
            break

    try:
        hints = typing.get_type_hints(model, localns=objects.__dict__)
    except Exception:  # noqa: BLE001
        return False
    field_type = hints.get(python_key)
    if field_type is None:
        return False
    if typing.get_origin(field_type) is dict:
        return True
    return any(typing.get_origin(arg) is dict for arg in typing.get_args(field_type))


def _normalize_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return _normalize_nested_dict(value)
    if isinstance(value, list):
        return [_normalize_nested(item) for item in value]
    return value


def _normalize_nested_dict(d: dict[str, Any]) -> dict[str, Any]:
    return {_normalize_key(k): _normalize_nested(v) for k, v in d.items()}


def _normalize_key(key: str) -> str:
    """Convert an OpenAPI key to the form pydantic expects for nested dicts.

    Keys starting with ``$`` (e.g. ``$ref``, ``$defs``, ``$dynamicRef``)
    are kept as-is because they are used verbatim as pydantic aliases.
    Other camelCase keys are converted to snake_case.

    """
    if key.startswith('$'):
        return key
    return _ALL_CAP_RE.sub(_REPLACEMENT_STR, _FIRST_CAP_RE.sub(_REPLACEMENT_STR, key)).lower()
