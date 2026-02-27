from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    TypeAlias,
    cast,
    final,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from dmr.openapi.objects.components import Components
    from dmr.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )
    from dmr.openapi.objects.info import Info
    from dmr.openapi.objects.path_item import PathItem
    from dmr.openapi.objects.paths import Paths
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.security_requirement import (
        SecurityRequirement,
    )
    from dmr.openapi.objects.server import Server
    from dmr.openapi.objects.tag import Tag

_OPENAPI_VERSION: Final = '3.1.0'

ConvertedSchema: TypeAlias = dict[str, Any]
_ConverterFunc: TypeAlias = Callable[['DataclassInstance'], ConvertedSchema]
_NormalizeKeyFunc: TypeAlias = Callable[[str], str]
_NormalizeValueFunc: TypeAlias = Callable[[Any, _ConverterFunc], Any]


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAPI:
    """This is the root object of the OpenAPI document."""

    openapi: str = _OPENAPI_VERSION

    info: 'Info'
    json_schema_dialect: str | None = None
    servers: 'list[Server] | None' = None
    paths: 'Paths | None' = None
    webhooks: 'dict[str, PathItem | Reference] | None' = None
    components: 'Components | None' = None
    security: 'list[SecurityRequirement] | None' = None
    tags: 'list[Tag] | None' = None
    external_docs: 'ExternalDocumentation | None' = None

    def convert(self) -> ConvertedSchema:
        """Convert the object to OpenAPI schema dictionary."""
        return convert(self)


def convert(to_convert: 'DataclassInstance') -> ConvertedSchema:
    """Converts any dataclass object into a json schema."""
    schema: ConvertedSchema = {}

    for field in fields(to_convert):
        schema_value = getattr(to_convert, field.name, None)
        if schema_value is None:
            continue

        schema[normalize_key(field.name)] = normalize_value(
            schema_value,
            convert,
        )

    return schema


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

    if key in {'param_in', 'security_scheme_in'}:
        return 'in'

    if key.startswith('schema_'):
        key = key.split('_', maxsplit=1)[-1]

    if '_' in key:
        components = key.split('_')
        return components[0].lower() + ''.join(
            component.title() for component in components[1:]
        )

    return key


# pyright: reportUnknownVariableType=false
def normalize_value(to_normalize: Any, converter: _ConverterFunc) -> Any:
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
        return converter(cast('DataclassInstance', to_normalize))

    if isinstance(to_normalize, list):
        return [
            normalize_value(list_item, converter) for list_item in to_normalize
        ]

    if isinstance(to_normalize, dict):
        return {
            normalize_value(dict_key, converter): normalize_value(
                dict_val,
                converter,
            )
            for dict_key, dict_val in to_normalize.items()
        }

    if isinstance(to_normalize, Enum):
        return to_normalize.value

    return to_normalize
