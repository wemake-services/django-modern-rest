from typing import TYPE_CHECKING

from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.openapi.objects import RequestBody
from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.operation import Operation
from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses

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
        request_body = self._generate_request_body(metadata)
        responses = self._generate_responses(metadata)
        return Operation(
            tags=metadata.tags,
            summary=metadata.summary,
            description=metadata.description,
            deprecated=metadata.deprecated,
            security=metadata.security,
            external_docs=metadata.external_docs,
            servers=metadata.servers,
            callbacks=metadata.callbacks,
            request_body=request_body,
            responses=responses,
        )

    def _generate_request_body(
        self,
        metadata: EndpointMetadata,
    ) -> RequestBody | None:
        """Generate request body from Body component."""
        if not metadata.component_parsers:
            return None

        for _, type_args in metadata.component_parsers:
            if type_args:
                sample_type = type_args[0]
                extractor = self.context.get_extractor(sample_type)
                return extractor.extract_request_body(
                    metadata.component_parsers,
                )

        return None

    def _generate_responses(
        self,
        metadata: EndpointMetadata,
    ) -> Responses | None:
        """Generate responses from ResponseSpecs."""
        if not metadata.responses:
            return None

        responses: Responses = {}
        for status_code, response_spec in metadata.responses.items():
            extractor = self.context.get_extractor(response_spec.return_type)
            schema = extractor.extract_schema(response_spec.return_type)

            responses[str(status_code.value)] = Response(
                description='Success',
                content={
                    'application/json': MediaType(schema=schema),
                },
            )

        return responses
