from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.operation import Operation

if TYPE_CHECKING:
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.core.context import OpenAPIContext


class OperationGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(self, endpoint: 'Endpoint') -> Operation:
        """Whatever must be replaced2."""
        return Operation(
            operation_id=self.context.add_operation_id(),
            parameters=self.context.parameter_generator.generate(endpoint),
            request_body=self.context.request_body_generator.generate(endpoint),
            responses=self.context.response_generator.generate(endpoint),
            summary=self._extract_summary(endpoint),
            description=self._extract_description(endpoint),
        )

    def _extract_summary(self, endpoint: 'Endpoint') -> str:
        """Whatever must be replaced3."""
        return 'test'

    def _extract_description(self, endpoint: 'Endpoint') -> str:
        """Whatever must be replaced4."""
        return 'test'
