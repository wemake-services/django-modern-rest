from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Literal, final

from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import TypedDict, TypeForm, override

from dmr.internal.types import find_annotated_metadata
from dmr.serializer import BaseSchemaGenerator, SchemaDef

if TYPE_CHECKING:
    from polyfactory.field_meta import FieldMeta


@final
class JsonSchemaKwargs(TypedDict, total=False, closed=True):
    """
    Keyword arguments for pydantic's ``json_schema`` method.

    .. versionadded:: 0.16.0
    """

    # `ref_template` is explicitly left out.
    # It is always computed from the OpenAPI schema registry.
    # `mode` is explicitly left out.
    # It is always defined by the `used_for_response` argument.
    by_alias: bool
    union_format: Literal['any_of', 'primitive_type_array']
    schema_generator: type[GenerateJsonSchema]


class PydanticSchemaGenerator(BaseSchemaGenerator):
    """
    Generates JSON schema for pydantic objects.

    Attributes:
        json_schema_kwargs: Dictionary of kwargs that will be passed
            to the ``json_schema`` method of pydantic's ``TypeAdapter``.

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
        model: TypeForm[Any],
        ref_template: str,
        *,
        used_for_response: bool = False,
    ) -> SchemaDef:
        """Proxies the JSON schema generation to pydantic itself."""
        from dmr.plugins.pydantic.serializer import (  # noqa: PLC0415
            _get_cached_type_adapter,  # pyright: ignore[reportPrivateUsage]
        )

        schema = _get_cached_type_adapter(model).json_schema(  # type: ignore[arg-type]
            ref_template=ref_template + '{model}',  # noqa: WPS336, RUF027
            mode='serialization' if used_for_response else 'validation',
            **cls.json_schema_kwargs,
        )
        components = schema.pop('$defs', {})
        return schema, components

    @override
    @classmethod
    def schema_name(cls, model: TypeForm[Any]) -> str | None:
        """Return a schema name for a model, if it exists."""
        try:
            schema = cls.get_schema(model, ref_template='')
        except Exception:
            return None
        return schema[0].get('title')

    @override
    @classmethod
    def field_examples(cls, field_meta: 'FieldMeta') -> Sequence[Any]:
        """
        Return examples from ``pydantic.Field(examples=[...])``.

        polyfactory keeps them in the field description of ``pydantic``
        models. Other models, like dataclasses, can have ``pydantic.Field``
        in ``Annotated`` metadata.

        .. versionadded:: 0.16.0
        """
        examples: Sequence[Any] | None = getattr(field_meta, 'examples', None)
        if examples:
            return examples
        field_info = find_annotated_metadata(field_meta.annotation, FieldInfo)
        annotated_examples: Sequence[Any] | None = getattr(
            field_info,
            'examples',
            None,
        )
        return annotated_examples or ()
