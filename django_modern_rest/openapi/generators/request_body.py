from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.request_body import RequestBody

if TYPE_CHECKING:
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.core.context import OpenAPIContext


class RequestBodyGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(self, endpoint: 'Endpoint') -> RequestBody:
        """Whatever must be replaced."""
        ...
