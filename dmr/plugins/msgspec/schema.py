from typing import Any

from msgspec.json import schema
from typing_extensions import override

from dmr.serializer import BaseSchemaGenerator, SchemaDef


class MsgspecSchemaGenerator(BaseSchemaGenerator):
    """Generates JSON schema for msgspec objects."""

    @override
    @classmethod
    def get_schema(
        cls,
        model: Any,
        ref_template: str,
        *,
        used_for_response: bool = False,
    ) -> SchemaDef | None:
        """Proxies the JSON schema generation to msgspec itself."""
        try:
            out = schema(
                model,
                ref_template=ref_template + '{name}',  # noqa: WPS336
            )
        except Exception:
            return None
        components = out.pop('$defs', {})
        return out, components

    @override
    @classmethod
    def schema_name(cls, model: Any) -> str | None:
        """Return a schema name for a model, if it exists."""
        schema = cls.get_schema(model, ref_template='')
        return schema[0].get('title') if schema else None
