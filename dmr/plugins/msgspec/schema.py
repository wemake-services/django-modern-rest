from collections.abc import Callable
from typing import Any, ClassVar, TypeAlias

from msgspec.json import schema
from typing_extensions import override

from dmr.serializer import BaseSchemaGenerator, SchemaDef

SchemaHook: TypeAlias = Callable[[type], dict[str, Any]]


class MsgspecSchemaGenerator(BaseSchemaGenerator):
    """
    Generates JSON schema for msgspec objects.

    Attributes:
        schema_hook: Callable that is called for each custom type
            that ``msgspec`` cannot describe natively.
            It must return a JSON schema dict for that type
            or raise ``NotImplementedError`` to use the default behavior.

    """

    __slots__ = ()

    schema_hook: ClassVar[SchemaHook | None] = None

    @override
    @classmethod
    def get_schema(
        cls,
        model: Any,
        ref_template: str,
        *,
        used_for_response: bool = False,
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
