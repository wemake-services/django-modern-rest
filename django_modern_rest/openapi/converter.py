from collections.abc import Callable, Iterator
from dataclasses import Field, fields, is_dataclass
from enum import Enum
from typing import Any, ClassVar, Protocol, TypeAlias, cast, final


class SchemaObject(Protocol):
    """Type that represents the `dataclass` object."""

    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]  # noqa: WPS234


ConvertedSchema: TypeAlias = dict[str, Any]
_ConverterFunc: TypeAlias = Callable[[SchemaObject], ConvertedSchema]
_NormalizeKeyFunc: TypeAlias = Callable[[str], str]
_NormalizeValueFunc: TypeAlias = Callable[[Any, _ConverterFunc], Any]


def normalize_key(key: str) -> str:
    """
    Convert a Python field name to an OpenAPI-compliant key.

    This function handles the conversion from Python naming conventions
    (snake_case) to OpenAPI naming conventions (camelCase) with special
    handling for reserved keywords and common patterns.

    Args:
        key: The Python field name to normalize

    Returns:
        The normalized key suitable for OpenAPI specification

    For example:

    .. code:: python
        >>> normalize_key('param_in')
        'in'
        >>> normalize_key('schema_not')
        'not'
        >>> normalize_key('external_docs')
        'externalDocs'
        >>> normalize_key('ref')
        '$ref'
        >>> normalize_key('content_media_type')
        'contentMediaType'
    """
    if key == 'ref':
        return '$ref'

    if key == 'param_in':
        return 'in'

    if key.startswith('schema_'):
        key = key.split('_', maxsplit=1)[-1]

    if '_' in key:
        components = key.split('_')
        return components[0].lower() + ''.join(
            component.title() for component in components[1:]
        )

    return key


# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
def normalize_value(to_normalize: Any, converter: '_ConverterFunc') -> Any:
    """
    Normalize a value for OpenAPI schema.

    Handles:
    - BaseObject instances (convert to schema dict)
    - Lists and sequences (process elements recursively)
    - Mappings (process keys and values recursively)
    - Primitive values (return as-is)
    - None values (should be filtered out by caller)
    """
    if is_dataclass(to_normalize):
        return converter(cast(SchemaObject, to_normalize))

    if isinstance(to_normalize, list):
        return [
            normalize_value(list_item, converter) for list_item in to_normalize
        ]

    if isinstance(to_normalize, dict):
        return {
            normalize_value(key, converter): normalize_value(val, converter)
            for key, val in to_normalize.items()  # noqa: WPS110
        }

    if isinstance(to_normalize, Enum):
        return to_normalize.value

    return to_normalize


@final
class SchemaConverter:
    """
    Convert the object to OpenAPI schema dictionary.

    This method iterates through all dataclass fields and converts them
    to OpenAPI-compliant format. Field names are normalized using
    `normalize_key` function, and values are recursively
    processed to handle nested objects, lists, and primitive types using
    `normalize_value` function.
    """

    # Private API:
    _normalize_key: _NormalizeKeyFunc = staticmethod(normalize_key)  # noqa: WPS421
    _normalize_value: _NormalizeValueFunc = staticmethod(normalize_value)  # noqa: WPS421

    @classmethod
    def convert(cls, schema_obj: SchemaObject) -> ConvertedSchema:
        """Convert the object to OpenAPI schema dictionary."""
        schema: ConvertedSchema = {}

        for field in cls._iter_fields(schema_obj):
            value = getattr(schema_obj, field.name, None)  # noqa: WPS110
            if value is None:
                continue

            schema[cls._normalize_key(field.name)] = cls._normalize_value(
                value,
                cls.convert,
            )

        return schema

    # Private API:
    @classmethod
    def _iter_fields(cls, schema_obj: SchemaObject) -> Iterator[Field[Any]]:
        yield from fields(schema_obj)
