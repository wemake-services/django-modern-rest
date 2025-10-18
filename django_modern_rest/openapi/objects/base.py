from collections.abc import Iterator
from dataclasses import Field, dataclass, fields
from enum import Enum
from typing import Any, TypeAlias

SchemaData: TypeAlias = dict[str, Any]


@dataclass(frozen=True, kw_only=True, slots=True)
class BaseObject:
    """Base class for schema spec objects."""

    def to_schema(self) -> SchemaData:
        """
        Convert the object to OpenAPI schema dictionary.

        This method iterates through all dataclass fields and converts them
        to OpenAPI-compliant format. Field names are normalized using
        snake_case to camelCase conversion, and values are recursively
        processed to handle nested objects, lists, and primitive types.
        """
        result: SchemaData = {}

        for field in self._iter_fields():
            value = getattr(self, field.name, None)
            if value is None:
                continue

            result[_normalize_key(field.name)] = _normalize_value(value)

        return result

    # Private API:
    def _iter_fields(self) -> Iterator[Field[Any]]:
        yield from fields(self)


def _normalize_key(key: str) -> str:
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
        >>> _normalize_key('param_in')
        'in'
        >>> _normalize_key('schema_not')
        'not'
        >>> _normalize_key('external_docs')
        'externalDocs'
        >>> _normalize_key('ref')
        '$ref'
        >>> _normalize_key('content_media_type')
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
def _normalize_value(value: Any) -> Any:
    """
    Normalize a value for OpenAPI schema.

    Handles:
    - BaseObject instances (convert to schema dict)
    - Lists and sequences (process elements recursively)
    - Mappings (process keys and values recursively)
    - Primitive values (return as-is)
    - None values (should be filtered out by caller)
    """
    if isinstance(value, BaseObject):
        return value.to_schema()

    if isinstance(value, list):
        return [_normalize_value(val) for val in value]

    if isinstance(value, dict):
        return {
            _normalize_key(str(key)): _normalize_value(val)
            for key, val in value.items()
        }

    if isinstance(value, Enum):
        return value.value

    return value
