from collections.abc import Callable
from typing import Any

from msgspec.json import schema
from typing_extensions import override

from dmr.serializer import BaseSchemaGenerator, SchemaDef


class MsgspecSchemaGenerator(BaseSchemaGenerator):
    """
    Generates JSON schema for msgspec objects.

    Schemas are registered and cached per annotation, not per serializer.

    Attributes:
        schema_hook: Custom callback to return schemas for unsupported types.
            If the same model is used by several serializers with different
            ``schema_hook`` implementations, only the hook of the serializer
            that generates the schema first will be applied.

    """

    __slots__ = ()

    schema_hook: Callable[[type[Any]], dict[str, Any]] | None = None

    @override
    @classmethod
    def get_schema(
        cls,
        model: Any,
        ref_template: str,
        *,
        used_for_response: bool = False,  # not used
    ) -> SchemaDef:
        """Proxies the JSON schema generation to msgspec itself."""
        out = schema(
            model,
            ref_template=ref_template + '{name}',  # noqa: WPS336
            schema_hook=cls.schema_hook,
        )
        components = out.pop('$defs', {})
        return out, components

    @override
    @classmethod
    def schema_name(cls, model: Any) -> str | None:
        """Return a schema name for a model, if it exists."""
        try:
            schema = cls.get_schema(model, ref_template='')
        except Exception:
            return None
        return schema[0].get('title')
