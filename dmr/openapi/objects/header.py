from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from dmr.internal.empty import EMPTY

if TYPE_CHECKING:
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@dataclass(kw_only=True, slots=True)
class Header:
    """
    Header Object.

    The Header Object follows the structure of the Parameter Object
    with the following changes:
    All traits that are affected by the location MUST be applicable to
    a location of header (for example, style).

    .. versionchanged:: 0.16.0
        ``content`` values can now be references.
        ``example`` now defaults to :data:`~dmr.types.EMPTY`
        instead of ``None``, because ``None`` is a valid value for it.

    """

    schema: 'Schema | None' = None
    description: str | None = None
    required: bool | None = None
    deprecated: bool | None = None
    style: str | None = None
    explode: bool | None = None
    example: Any = EMPTY
    examples: dict[str, 'Example | Reference'] | None = None
    content: dict[str, 'MediaType | Reference'] | None = None
