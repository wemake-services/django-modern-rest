import dataclasses
from typing import TYPE_CHECKING

from dmr.openapi.objects.responses import Responses

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseGenerator:
    """Generator for OpenAPI ``Response`` objects."""

    _context: 'OpenAPIContext'

    def __call__(
        self,
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> Responses:
        """Generate responses from response specs."""
        return {
            str(status_code.value): response_spec.get_schema(
                serializer,
                self._context,
                metadata,
            )
            for status_code, response_spec in metadata.responses.items()
        }
