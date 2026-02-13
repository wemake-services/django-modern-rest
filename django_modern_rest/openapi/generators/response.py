import dataclasses
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata
    from django_modern_rest.openapi.core.context import OpenAPIContext


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseGenerator:
    """Generator for OpenAPI ``Response`` objects."""

    _context: 'OpenAPIContext'

    def __call__(self, metadata: 'EndpointMetadata') -> Responses:
        """Generate responses from response specs."""
        return {
            str(status_code.value): Response(
                description=status_code.phrase,
                content={
                    req_parser.content_type: MediaType(
                        schema=self._context.generators.schema(
                            response_spec.return_type,
                        ),
                    )
                    for req_parser in metadata.parsers.values()
                },
            )
            for status_code, response_spec in metadata.responses.items()
        }
