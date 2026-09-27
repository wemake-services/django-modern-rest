from collections.abc import Callable
from typing import Any, ClassVar, final

from msgspec.json import schema
from typing_extensions import TypedDict, override

from dmr.serializer import BaseSchemaGenerator, SchemaDef


@final
class JsonSchemaKwargs(TypedDict, total=False, closed=True):
    """
    Keyword arguments for msgspec's ``json_schema`` method.

    .. versionadded:: 0.16.0
    """

    # `ref_template` is explicitly left out.
    # It is always computed from the OpenAPI schema registry.
    schema_hook: Callable[[type[Any]], dict[str, Any]] | None


class MsgspecSchemaGenerator(BaseSchemaGenerator):
    """
    Generates JSON schema for msgspec objects.

    Attributes:
        json_schema_kwargs: Dictionary of kwargs that will be passed
            to the :func:`!msgspec.json.schema` function.

    Schemas are registered and cached per annotation, not per serializer.

    .. versionchanged:: 0.16.0
        Added ``json_schema_kwargs``.

    """

    __slots__ = ()

    json_schema_kwargs: ClassVar[JsonSchemaKwargs] = {}

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
            **cls.json_schema_kwargs,
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
