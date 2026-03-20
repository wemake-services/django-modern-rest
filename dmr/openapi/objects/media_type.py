from collections.abc import Hashable
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, final

from typing_extensions import override

if TYPE_CHECKING:
    from dmr.openapi.objects.encoding import Encoding
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@final
@dataclass(kw_only=True, slots=True, frozen=True)
class MediaTypeMetadata:
    """Media type metadata to be set on a request body."""

    # NOTE: defaults here must match defaults of `MediaType`:
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None
    encoding: dict[str, 'Encoding'] | None = None

    # OpenAPI 3.2+ fields:
    item_encoding: 'Encoding | None' = None
    prefix_encoding: 'Encoding | None' = None

    @override
    def __hash__(self) -> int:
        """Hash the dataclass in a safe way."""
        return sum(
            hash(field)  # type: ignore[misc]
            for field in asdict(self)
            if isinstance(field, Hashable)  # type: ignore[redundant-expr]
        )


@dataclass(kw_only=True, slots=True)
class MediaType:
    """
    Media Type Object.

    Each Media Type Object provides schema and examples for the media
    type identified by its key.
    """

    # Can be `None` only when `item_schema` is set:
    schema: 'Reference | Schema | None' = None
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None
    encoding: dict[str, 'Encoding'] | None = None

    # OpenAPI 3.2+ fields:
    item_schema: 'Reference | Schema | None' = None
    item_encoding: 'Encoding | None' = None
    prefix_encoding: 'Encoding | None' = None

    def __post_init__(self) -> None:
        """Validate the object."""
        if self.schema is None and self.item_schema is None:
            raise ValueError('Both `schema` and `item_schema` cannot be None')
        if self.encoding and (self.item_encoding or self.prefix_encoding):
            raise ValueError(
                'Both `encoding` and `item_encoding` or `prefix_encoding` '
                'cannot be set',
            )
