from typing import TYPE_CHECKING

from django_modern_rest.openapi.collector import ControllerMapping
from django_modern_rest.openapi.objects.path_item import PathItem

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


class PathItemGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(self, mapping: ControllerMapping) -> PathItem:
        """Whatever must be replaced."""
        path_item = PathItem()  # TODO: Make it frozen

        for method, endpoint in mapping.controller.api_endpoints.items():
            operation = self.context.operation_generator.generate(endpoint)
            setattr(path_item, method.lower(), operation)
        return path_item
