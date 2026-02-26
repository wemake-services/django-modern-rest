import dataclasses
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, final

from django.http.request import HttpRequest, MediaType
from django.http.response import HttpResponseBase

from dmr.exceptions import NotAcceptableError

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata
    from dmr.negotiation import ContentType
    from dmr.parsers import Parser
    from dmr.renderers import Renderer


@final
@dataclasses.dataclass(slots=True, frozen=True)
class ConditionalType:
    """
    Internal type that we use as a metadata.

    Public API is to use
    :func:`dmr.negotiation.conditional_type` instead of this.
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
    renderer: 'Renderer | None',
    metadata: 'EndpointMetadata',
) -> 'Parser':
    """
    Special type that we use to re-parse our own response body.

    We do this only when response validation is active.
    It should not be used in production directly.
    Think of it as an internal validation helper.
    """
    parsers = metadata.parsers
    if renderer is not None:
        return renderer.validation_parser

    # `renderer` can be `None` when `Accept` header
    # is broken / missing / incorrect.
    # Then, we fallback to the types we know.
    content_type = response.headers['Content-Type']

    # Our last resort is to get the default renderer type.
    # It is always present.
    return parsers.get(
        content_type,
        # If nothing works, fallback to the default parser:
        next(iter(parsers.values())),
    )


def media_by_precedence(content_types: Iterable[str]) -> list[MediaType]:
    """Return sorted content types based on specificity and quality."""
    return sorted(
        (
            media_type
            for content_type in content_types
            if (media_type := MediaType(content_type)).quality != 0
        ),
        key=lambda media: (media.specificity, media.quality),
        reverse=True,
    )


def force_request_renderer(request: HttpRequest, renderer: 'Renderer') -> None:
    """Forces *renderer* to be used for the *request*."""
    request.__dmr_renderer__ = renderer  # type: ignore[attr-defined]


def negotiate_renderer(
    request: HttpRequest,
    renderers: Mapping[str, 'Renderer'],
    *,
    default: 'Renderer | None' = None,
) -> 'Renderer':
    """
    Choose a renderer by the request's Accept header.

    When Accept is missing, returns *default* (or the first renderer).
    Raises :exc:`~dmr.exceptions.NotAcceptableError` when Accept is set
    and does not match any of *renderers*.
    """
    renderer_keys = list(renderers.keys())
    fallback = next(iter(renderers.values())) if default is None else default

    if request.headers.get('Accept') is None:
        return fallback

    renderer_type = request.get_preferred_type(renderer_keys)
    if renderer_type is None:
        supported = renderer_keys
        raise NotAcceptableError(
            'Cannot serialize response body '
            f'with accepted types {request.accepted_types!r}, '
            f'{supported=!r}',
        )
    return renderers[renderer_type]
