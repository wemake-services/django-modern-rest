from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.operation import Operation

if TYPE_CHECKING:
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.core.context import OpenAPIContext


class OperationGenerator:
    """
    Generator for OpenAPI Operation objects.

    The Operation Generator is responsible for creating OpenAPI Operation
    objects that describe individual API operations (HTTP methods like GET,
    POST, etc.) for a specific endpoint. It extracts metadata from the
    endpoint and generates a complete Operation specification.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the Operation Generator."""
        self.context = context

    def generate(self, endpoint: 'Endpoint') -> Operation:
        """Generate an OpenAPI Operation from an endpoint."""
        metadata = endpoint.metadata
        return Operation(
            tags=metadata.tags,
            summary=metadata.summary,
            description=metadata.description,
            deprecated=metadata.deprecated,
            security=metadata.security,
            external_docs=metadata.external_docs,
            servers=metadata.servers,
            callbacks=metadata.callbacks,
            # TODO: implement another attributes generation.
        )
