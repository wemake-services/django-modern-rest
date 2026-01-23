import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from django_modern_rest.negotiation import ContentType


@final
@dataclasses.dataclass(slots=True, frozen=True)
class ContentNegotiation:
    """
    Internal type that we use as a metadata.

    Public API is to use
    :func:`django_modern_rest.negotiation.content_negotiation` instead of this.
    """

    original: tuple[tuple['ContentType', Any], ...]
    computed: Mapping[str, Any] = dataclasses.field(
        hash=False,
        init=False,
    )

    def __post_init__(self) -> None:
        """
        Post process passed objects.

        What we do here:
        1. We have to have `_ContentNegotiation` hashable, so it can be cached
        2. We pass dict as pairs of tuples
        3. Then we pre-compute the dict back

        It wastes extra memory, but we are fine with that.
        Because objects will be rather small.
        It is Python after all!
        """
        object.__setattr__(self, 'computed', dict(self.original))
