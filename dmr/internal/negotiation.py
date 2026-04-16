import dataclasses
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Final, final

from django.http.request import HttpRequest, MediaType
from django.http.response import HttpResponseBase
from django.utils.translation import gettext_lazy as _

from dmr.compiled import accepted_type
from dmr.exceptions import NotAcceptableError, ResponseSchemaError

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata
    from dmr.parsers import Parser
    from dmr.renderers import Renderer

_WRONG_NEGOTIATION_MSG: Final = _(
    'Negotiated renderer {renderer_type} does not match'
    ' returned content-type {content_type}',
)

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


def negotiatiate_response_validation(
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
    # `renderer` can be `None` when `Accept` header
    # is broken / missing / incorrect.
    # Then, we fallback to the types we know.
    content_type = response.headers.get('Content-Type')
    if renderer is not None:
        if content_type is None or renderer.content_type == content_type:
            return renderer.validation_parser

        # If the content types do not match, we need to raise an error,
        # most likely user made a mistake somewhere:
        if (
            renderer.content_type != content_type
            and metadata.validate_negotiation
            # Streaming responses have a different logic:
            and not getattr(response, 'streaming', False)
        ):
            raise ResponseSchemaError(
                _WRONG_NEGOTIATION_MSG.format(
                    renderer_type=repr(renderer.content_type),
                    content_type=repr(content_type),
                ),
            )

    # Our last resort is to get the default renderer type.
    # It is always present.
    return metadata.parsers.get(  # pyrefly: ignore[no-matching-overload]
        content_type,  # type: ignore[arg-type]
        # If nothing works, fallback to the default parser:
        next(iter(metadata.parsers.values())),
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
