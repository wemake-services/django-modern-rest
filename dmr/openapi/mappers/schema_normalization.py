import dataclasses
from collections.abc import Callable
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    TypeAlias,
    TypeVar,
    cast,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


DumpedSchema: TypeAlias = dict[str, Any]
_ConverterFunc: TypeAlias = Callable[['DataclassInstance'], DumpedSchema]
_NormalizeKeyFunc: TypeAlias = Callable[[str], str]
_NormalizeValueFunc: TypeAlias = Callable[[Any, _ConverterFunc], Any]

_DataclassT = TypeVar('_DataclassT', bound='DataclassInstance')


def load_schema(
    unstructured: dict[str, Any],
    model: type[_DataclassT],
) -> _DataclassT:
    """
    Load *unstructured* schema into the *model* dataclass type.

    Used to include external schemas into the DMR-based project.
    Only works with ``pydantic`` installed:

    .. bash::

        pip install 'django-modern-rest[pydantic]'

    .. versionadded:: 0.13.0
    """
    # So we can use it as a namespace:
    from dmr.openapi import objects  # noqa: PLC0415, I001

    # So it would have a nice error message:
    from dmr.plugins.pydantic import PydanticFastSerializer  # noqa: PLC0415

    # Must be after our import:
    import pydantic  # noqa: PLC0415
    from pydantic import alias_generators  # noqa: PLC0415, WPS458

    # We define a model that will automatically convert all *needed* dicts's
    # keys from camelCase into a snake_case. By default OpenAPI uses camelCase.
    @pydantic.dataclasses.dataclass(
        config=pydantic.ConfigDict(alias_generator=alias_generators.to_camel),
    )
    class CamelModel(model): ...  # type: ignore[valid-type, misc]  # noqa: WPS431, WPS604

    return PydanticFastSerializer.from_python(  # type: ignore[no-any-return]
        unstructured,
        CamelModel,
        strict=False,
        extra_namespace=objects.__dict__,
    )


def dump_schema(to_convert: 'DataclassInstance') -> DumpedSchema:  # noqa: WPS231
    """
    Converts any our dataclass OpenAPI object into a JSON schema.

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

        schema[_dump_field(field.name, field.type)] = _dump_value(
            schema_value,
        )

    return schema


def _dump_field(key: str, field_type: Any) -> str:
    """
    Convert a Python field name to an OpenAPI-compliant key.

    This function handles the conversion from Python naming conventions
    (snake_case) to OpenAPI naming conventions (camelCase) with special
    handling for reserved keywords and common patterns.

    Args:
        key: The Python field name to normalize.
        field_type: Field type that can contain ``Field()`` metadata.

    Returns:
        The normalized key suitable for OpenAPI specification

    """
    from dmr.internal.dataclass_aliases import FieldInfo  # noqa: PLC0415
    from dmr.metadata import get_annotated_metadata  # noqa: PLC0415

    field_meta = get_annotated_metadata(field_type, FieldInfo)
    if field_meta:
        return field_meta.alias

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
    - Enums (return value)

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
