from typing import Any, ClassVar

import pydantic
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode
from pydantic_core import CoreSchema
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.plugins.pydantic.schema import (
    JsonSchemaKwargs,
    PydanticSchemaGenerator,
)


class NoTitleJsonSchema(GenerateJsonSchema):
    """Drops ``title`` keys from the generated schemas."""

    @override
    def generate(
        self,
        schema: CoreSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        """Generate a JSON schema and remove its title."""
        json_schema = super().generate(schema, mode=mode)
        json_schema.pop('title', None)
        return json_schema


class SchemaGenerator(PydanticSchemaGenerator):
    json_schema_kwargs: ClassVar[JsonSchemaKwargs] = {
        'schema_generator': NoTitleJsonSchema,
    }


class NoTitleSerializer(PydanticSerializer):
    schema_generator = SchemaGenerator


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[NoTitleSerializer]):
    def get(self) -> UserModel:
        return UserModel(email='user@example.com')


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
