from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference


@dataclass(kw_only=True, slots=True)
class RequestBody:
    """
    Describes a single request body.

    .. versionchanged:: 0.16.0
        ``content`` values can now be references.

    """

    content: dict[str, 'MediaType | Reference']
    description: str | None = None
    required: bool | None = True
