from collections.abc import Callable
from dataclasses import is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeAlias, cast

if TYPE_CHECKING:
    from django_modern_rest.openapi.converter import ConverterFunc, SchemaObject

NormalizeKeyFunc: TypeAlias = Callable[[str], str]
NormalizeValueFunc: TypeAlias = Callable[[Any, 'ConverterFunc'], Any]


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
def normalize_value(value: Any, converter: 'ConverterFunc') -> Any:  # noqa: WPS110
    """
    Normalize a value for OpenAPI schema.

    Handles:
    - BaseObject instances (convert to schema dict)
    - Lists and sequences (process elements recursively)
    - Mappings (process keys and values recursively)
    - Primitive values (return as-is)
    - None values (should be filtered out by caller)
    """
    if is_dataclass(value):
        return converter(cast('SchemaObject', value))

    if isinstance(value, list):
        return [normalize_value(val, converter) for val in value]  # noqa: WPS110

    if isinstance(value, dict):
        return {
            normalize_key(str(key)): normalize_value(val, converter)
            for key, val in value.items()  # noqa: WPS110
        }

    if isinstance(value, Enum):
        return value.value

    return value
