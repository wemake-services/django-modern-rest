from typing import Any

from typing_extensions import override

from dmr.serializer import BaseSchemaGenerator, SchemaDef


class PydanticSchemaGenerator(BaseSchemaGenerator):
    """Generates JSON schema for pydantic objects."""

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
