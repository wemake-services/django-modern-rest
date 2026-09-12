from typing import Any

import pydantic
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from typing_extensions import override

from dmr.plugins.pydantic.schema import PydanticSchemaGenerator


class _Model(pydantic.BaseModel):
    """Simple model used to exercise schema generation."""

    name: str


class _CustomGenerateJsonSchema(GenerateJsonSchema):
    """Adds a marker key so tests can prove this class was actually used."""

    @override
    def generate(
        self,
        schema: Any,
        mode: str = 'validation',
    ) -> JsonSchemaValue:
        json_schema = super().generate(schema, mode=mode)  # type: ignore[arg-type]
        json_schema['x-custom'] = True
        return json_schema


class _CustomPydanticSchemaGenerator(PydanticSchemaGenerator):
    """Subclass plugging in a custom ``GenerateJsonSchema``."""

    __slots__ = ()

    schema_generator = _CustomGenerateJsonSchema


def test_default_schema_generator_is_unaffected() -> None:
    """The default `PydanticSchemaGenerator` behavior is unchanged."""
    schema, _ = PydanticSchemaGenerator.get_schema(
        _Model,
        ref_template='#/components/schemas/',
    )

    assert 'x-custom' not in schema


def test_custom_schema_generator_is_used() -> None:
    """A subclass can override `schema_generator` to customize output."""
    schema, _ = _CustomPydanticSchemaGenerator.get_schema(
        _Model,
        ref_template='#/components/schemas/',
    )

    assert schema['x-custom'] is True
