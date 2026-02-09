import dataclasses
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, final

from django.http import HttpRequest
from django.http.response import HttpResponseBase

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata
    from django_modern_rest.negotiation import ContentType
    from django_modern_rest.parsers import Parser
    from django_modern_rest.renderers import Renderer


@final
@dataclasses.dataclass(slots=True, frozen=True)
class ConditionalType:
    """
    Internal type that we use as a metadata.

    Public API is to use
    :func:`django_modern_rest.negotiation.conditional_type` instead of this.
    """

    _original: tuple[tuple['ContentType', Any], ...]
    computed: Mapping[str, Any] = dataclasses.field(
        hash=False,
        init=False,
    )

    def __post_init__(self) -> None:
        """
        Post process passed objects.

        What we do here:
        1. We have to have `_ConditionalType` hashable, so it can be cached
        2. We pass dict as pairs of tuples
        3. Then we pre-compute the dict back

        It wastes extra memory, but we are fine with that.
        Because objects will be rather small.
        It is Python after all!
        """
        object.__setattr__(self, 'computed', dict(self._original))


def response_validation_negotiator(
    request: HttpRequest,
    response: HttpResponseBase,
    renderer_type: type['Renderer'] | None,
    metadata: 'EndpointMetadata',
) -> type['Parser']:
    """
    Special type that we use to re-parse our own response body.

    We do this only when response validation is active.
    It should not be used in production directly.
    Think of it as an internal validation helper.
    """
    parser_types = metadata.parsers
    if renderer_type is None:
        # We can fail to find `request_renderer` when `Accept` header
        # is broken / missing / incorrect.
        # Then, we fallback to the types we know.
        content_type = response.headers['Content-Type']
    else:
        content_type = renderer_type.content_type

    # Our last resort is to get the default renderer type.
    # It is always present.
    return parser_types.get(
        content_type,
        next(reversed(parser_types.values())),
    )
