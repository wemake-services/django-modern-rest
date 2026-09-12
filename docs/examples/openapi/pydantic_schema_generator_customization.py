from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.plugins.pydantic.schema import PydanticSchemaGenerator


class MyGenerateJsonSchema(GenerateJsonSchema):
    """Any customization pydantic's `GenerateJsonSchema` supports."""

    @override
    def generate(
        self,
        schema: object,
        mode: str = 'validation',
    ) -> JsonSchemaValue:
        json_schema = super().generate(schema, mode=mode)  # type: ignore[arg-type]
        json_schema['x-generated-by'] = 'my-generator'
        return json_schema


class MyPydanticSchemaGenerator(PydanticSchemaGenerator):
    """Plugs `MyGenerateJsonSchema` into pydantic schema generation."""

    __slots__ = ()

    schema_generator = MyGenerateJsonSchema
    union_format = 'primitive_type_array'


class MySerializer(PydanticSerializer):
    """Serializer using the customized schema generator."""

    __slots__ = ()

    schema_generator = MyPydanticSchemaGenerator
