from collections.abc import Callable, Iterator
from dataclasses import Field, fields
from typing import Any, ClassVar, Protocol, TypeAlias, final

from django_modern_rest.openapi.normalizers import (
    NormalizeKeyFunc,
    NormalizeValueFunc,
    normalize_key,
    normalize_value,
)


class SchemaObject(Protocol):
    """Type that represents the `dataclass` object."""

    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]  # noqa: WPS234


ConvertedSchema: TypeAlias = dict[str, Any]
ConverterFunc: TypeAlias = Callable[[SchemaObject], ConvertedSchema]


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

    def __init__(
        self,
        normalize_key: NormalizeKeyFunc = normalize_key,
        normalize_value: NormalizeValueFunc = normalize_value,
    ) -> None:
        """Allow to inject normalization function."""
        self.normalize_key = normalize_key
        self.normalize_value = normalize_value

    def convert(self, schema_obj: SchemaObject) -> ConvertedSchema:
        """Convert the object to OpenAPI schema dictionary."""
        schema: ConvertedSchema = {}

        for field in self._iter_fields(schema_obj):
            value = getattr(schema_obj, field.name, None)  # noqa: WPS110
            if value is None:
                continue

            schema[self.normalize_key(field.name)] = self.normalize_value(
                value,
                self.convert,
            )

        return schema

    # Private API:
    def _iter_fields(self, schema_obj: SchemaObject) -> Iterator[Field[Any]]:
        yield from fields(schema_obj)
