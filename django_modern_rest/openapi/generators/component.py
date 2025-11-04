from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects import Paths
from django_modern_rest.openapi.objects.components import Components

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


class ComponentGenerator:
    """
    Generator for OpenAPI Components section.

    The Components Generator is responsible for extracting and organizing
    reusable objects from the API specification. It processes all path items
    to identify shared components like schemas, parameters, responses,
    request bodies, headers, examples, security schemes, links, and callbacks
    that can be referenced throughout the OpenAPI specification.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the Components Generator."""
        self.context = context

    def generate(self, paths_items: Paths) -> Components:
        """Generate OpenAPI Components from path items."""
        schemas = self.context.schema_registry.all()
        return Components(schemas=schemas or None)
