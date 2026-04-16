import dataclasses
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Final, final

from django.http.request import HttpRequest, MediaType
from django.http.response import HttpResponseBase
from django.utils.translation import gettext_lazy as _

from dmr.compiled import accepted_type
from dmr.exceptions import NotAcceptableError

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata
    from dmr.parsers import Parser
    from dmr.renderers import Renderer

_CANNOT_SERIALIZE_MSG: Final = _(
    'Cannot serialize response body with'
    ' accepted types {accepted_types},'
    ' supported={supported}',
)


@final
@dataclasses.dataclass(slots=True, frozen=True)
class ConditionalType:
    """
    Internal type that we use as metadata.

    Public API is to use
    :func:`dmr.negotiation.conditional_type` instead of this.
    """

    computed: Mapping[str, Any] = dataclasses.field(hash=False)


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


def negotiate_renderer(
    request: HttpRequest,
    renderers: Mapping[str, 'Renderer'],
    *,
    default: 'Renderer',
) -> 'Renderer':
    """
    Choose a renderer by the request's Accept header.

    When Accept is missing, returns *default* (or the first renderer).
    Raises :exc:`~dmr.exceptions.NotAcceptableError` when Accept is set
    and does not match any of *renderers*.
    """
    accept = request.headers.get('Accept')
    if accept is None:
        return default

    renderer_type = accepted_type(accept, renderers)
    if renderer_type is None:
        raise NotAcceptableError(
            _CANNOT_SERIALIZE_MSG.format(
                accepted_types=repr(request.accepted_types),
                supported=repr(list(renderers)),
            ),
        )
    return renderers[renderer_type]
