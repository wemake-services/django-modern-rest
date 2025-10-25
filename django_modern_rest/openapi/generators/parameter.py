from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.parameter import Parameter
from django_modern_rest.openapi.objects.reference import Reference

if TYPE_CHECKING:
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.core.context import OpenAPIContext


class ParameterGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(self, endpoint: 'Endpoint') -> list[Parameter | Reference]:
        """Whatever must be replaced."""
        return [Reference(ref='foo')]  # TODO:
