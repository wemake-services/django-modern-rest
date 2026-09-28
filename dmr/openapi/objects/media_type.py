from collections.abc import Hashable
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, final

from typing_extensions import override

from dmr.internal.empty import EMPTY

if TYPE_CHECKING:
    from dmr.openapi.objects.encoding import Encoding
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@final
@dataclass(kw_only=True, slots=True, frozen=True)
class MediaTypeMetadata:
    """
    Media type metadata to be set on a request body.

    .. versionchanged:: 0.16.0
        Added ``description`` from OpenAPI 3.2.
        ``prefix_encoding`` is now a list, as the spec requires.
        ``example`` now defaults to :data:`~dmr.types.EMPTY`
        instead of ``None``, because ``None`` is a valid value for it.

    """

    # NOTE: defaults here must match defaults of `MediaType`:
    example: Any = EMPTY
    examples: dict[str, 'Example | Reference'] | None = None
    encoding: dict[str, 'Encoding'] | None = None

    # OpenAPI 3.2+ fields:
    description: str | None = None
    item_encoding: 'Encoding | None' = None
    prefix_encoding: list['Encoding'] | None = None

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

    .. versionchanged:: 0.16.0
        Added ``description`` from OpenAPI 3.2.
        ``prefix_encoding`` is now a list, as the spec requires.
        ``example`` now defaults to :data:`~dmr.types.EMPTY`
        instead of ``None``, because ``None`` is a valid value for it.

    """

    # Can be `None` only when `item_schema` is set:
    schema: 'Schema | None' = None
    example: Any = EMPTY
    examples: dict[str, 'Example | Reference'] | None = None
    encoding: dict[str, 'Encoding'] | None = None

    # OpenAPI 3.2+ fields:
    # NOTE: `encoding` is mutually exclusive with the two `*_encoding` ones,
    # we let `openapi-spec-validator` report that.
    description: str | None = None
    item_schema: 'Schema | None' = None
    item_encoding: 'Encoding | None' = None
    prefix_encoding: list['Encoding'] | None = None
