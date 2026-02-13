import dataclasses
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.request_body import RequestBody

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata
    from django_modern_rest.openapi.core.context import OpenAPIContext


@dataclasses.dataclass(frozen=True, slots=True)
class RequestBodyGenerator:
    """Generator for OpenAPI ``RequestBody`` objects."""

    _context: 'OpenAPIContext'

    def __call__(self, metadata: 'EndpointMetadata') -> RequestBody | None:
        """Generate request body from parsers."""
        for parser, model in metadata.component_parsers:
            # TODO: Do we need enum for context name?
            if parser.context_name != 'parsed_body':
                continue

            reference = self._context.generators.schema(model[0])
            return RequestBody(
                content={
                    req_parser.content_type: MediaType(schema=reference)
                    for req_parser in metadata.parsers.values()
                },
                required=True,
            )
        return None
