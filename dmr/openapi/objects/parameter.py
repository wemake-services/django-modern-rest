from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeAlias

from dmr.internal.dataclass_aliases import Field

if TYPE_CHECKING:
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema

#: Location of a single operation parameter.
ParameterLocation: TypeAlias = Literal[
    'query',
    # OpenAPI 3.2+, treats the whole query string as a single value:
    'querystring',
    'header',
    'path',
    'cookie',
]


@dataclass(unsafe_hash=True, kw_only=True, slots=True)
class ParameterMetadata:
    """Describes metadata for a single operation parameter."""

    description: str | None = None
    deprecated: bool | None = None
    allow_empty_value: bool | None = None
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool | None = None
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None


@dataclass(kw_only=True, slots=True)
class Parameter(ParameterMetadata):
    """
    Describes a single operation parameter.

    .. versionchanged:: 0.16.0
        ``param_in`` is now typed, it also allows ``'querystring'``
        from OpenAPI 3.2. ``content`` values can now be references.

    """

    name: str
    param_in: Annotated[ParameterLocation, Field(alias='in')]
    schema: 'Reference | Schema | None' = None
    content: dict[str, 'MediaType | Reference'] | None = None
    required: bool = False

    def __post_init__(self) -> None:
        """Validate the object."""
        if self.param_in != 'querystring':
            return
        # The whole query string is a single value, it cannot be described
        # by a `schema` with the RFC6570-style serialization fields.
        if self.content is None or self.schema is not None:
            raise ValueError(
                '`querystring` parameters must use `content`, not `schema`',
            )
