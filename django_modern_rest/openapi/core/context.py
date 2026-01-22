from typing import TYPE_CHECKING

from django_modern_rest.openapi.core.registry import OperationIdRegistry
from django_modern_rest.openapi.generators.operation import (
    OperationGenerator,
    OperationIDGenerator,
)

if TYPE_CHECKING:
    from django_modern_rest.openapi.config import OpenAPIConfig


class OpenAPIContext:
    """
    Context for OpenAPI specification generation.

    Maintains shared state and generators used across the OpenAPI
    generation process. Provides access to different generators.
    """

    def __init__(
        self,
        config: 'OpenAPIConfig',
    ) -> None:
        """Initialize the OpenAPI context."""
        self.config = config

        # Initialize generators once with shared context:
        self.operation_id_registry = OperationIdRegistry()

        self.operation_generator = OperationGenerator(self)
        self.operation_id_generator = OperationIDGenerator(self)
