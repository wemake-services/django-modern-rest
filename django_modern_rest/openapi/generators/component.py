import dataclasses
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects import Paths
from django_modern_rest.openapi.objects.components import Components

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentGenerator:
    """
    Generator for OpenAPI Components section.

    The ``Components`` Generator is responsible for extracting and organizing
    reusable objects from the API specification. It processes all path items
    to identify shared components like schemas, parameters, responses,
    request bodies, headers, examples, security schemes, links, and callbacks
    that can be referenced throughout the OpenAPI specification.
    """

    _context: 'OpenAPIContext'

    def __call__(self, paths_items: Paths) -> Components:
        """Generate OpenAPI Components from path items."""
        return Components(schemas=self._context.registries.schema.schemas)
