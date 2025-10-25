import uuid
from typing import TYPE_CHECKING

from django_modern_rest.openapi.generators.header import HeaderGenerator
from django_modern_rest.openapi.generators.operation import OperationGenerator
from django_modern_rest.openapi.generators.parameter import ParameterGenerator
from django_modern_rest.openapi.generators.request_body import (
    RequestBodyGenerator,
)
from django_modern_rest.openapi.generators.response import ResponseGenerator
from django_modern_rest.types import Empty, EmptyObj

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
        self._operation_ids: set[str] = set()

        # Initialize generators once with shared context:
        self.parameter_generator = ParameterGenerator(self)
        self.request_body_generator = RequestBodyGenerator(self)
        self.response_generator = ResponseGenerator(self)
        self.operation_generator = OperationGenerator(self)
        self.header_generator = HeaderGenerator(self)

    def add_operation_id(self, operation_id: str | Empty = EmptyObj) -> str:
        """Add or generate a unique operation ID."""
        if isinstance(operation_id, Empty):
            # TODO: bug, not unique
            operation_id = uuid.uuid4().hex  # TODO: temporary solution

        if operation_id in self._operation_ids:
            raise ValueError(f"Duplicate operation_id: '{operation_id}")

        self._operation_ids.add(operation_id)
        return operation_id
