from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses
from django_modern_rest.response import ResponseDescription

if TYPE_CHECKING:
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.core.context import OpenAPIContext


class ResponseGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever mus123t be replaced."""
        self.context = context

    def generate(self, endpoint: 'Endpoint') -> Responses:
        """Whatever must be replacedasd."""
        responses: Responses = {}

        for method, description in endpoint.metadata.responses.items():
            responses[str(method)] = self._create_response(description)

        return responses

    def _create_response(
        self,
        description: ResponseDescription,
    ) -> Response:
        """Whatever must be replaced."""
        return Response(
            description='test',
            headers=self.context.header_generator.generate(description.headers),
        )
