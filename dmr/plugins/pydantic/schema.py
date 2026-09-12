from typing import Any, Literal

from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import override

from dmr.serializer import BaseSchemaGenerator, SchemaDef


class PydanticSchemaGenerator(BaseSchemaGenerator):
    """Generates JSON schema for pydantic objects."""

    __slots__ = ()

    #: Subclass and override to customize the ``GenerateJsonSchema``
    #: class pydantic uses to build the schema.
    schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema

    #: Subclass and override to customize how pydantic renders unions.
    union_format: Literal['any_of', 'primitive_type_array'] = 'any_of'

    @override
    @classmethod
    def get_schema(
        cls,
        model: Any,
        ref_template: str,
        *,
        used_for_response: bool = False,
    ) -> SchemaDef:
        """Proxies the JSON schema generation to pydantic itself."""
        from dmr.plugins.pydantic.serializer import (  # noqa: PLC0415
            _get_cached_type_adapter,  # pyright: ignore[reportPrivateUsage]
        )

        schema = _get_cached_type_adapter(model).json_schema(
            ref_template=ref_template + '{model}',  # noqa: WPS336, RUF027
            mode='serialization' if used_for_response else 'validation',
            schema_generator=cls.schema_generator,
            union_format=cls.union_format,
        )
        components = schema.pop('$defs', {})
        return schema, components

    @override
    @classmethod
    def schema_name(cls, model: Any) -> str | None:
        """Return a schema name for a model, if it exists."""
        try:
            schema = cls.get_schema(model, ref_template='')
        except Exception:
            return None
        return schema[0].get('title')
