from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects import Paths
from django_modern_rest.openapi.objects.components import Components

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


class ComponentGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(self, paths_items: Paths) -> Components:
        """Whatever must be replaced."""
