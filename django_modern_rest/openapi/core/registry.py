class OperationIdRegistry:
    """Registry for OpenAPI operation IDs."""

    def __init__(self) -> None:
        """Initialize an empty operation ids registry."""
        self._operation_ids: set[str] = set()

    def register(self, operation_id: str) -> None:
        """Register a operation ID in the registry."""
        if operation_id in self._operation_ids:
            raise ValueError(
                f'Operation ID {operation_id!r} is already registered in the '
                'OpenAPI specification. Operation IDs must be unique across '
                'all endpoints to ensure proper API documentation. '
                'Please use a different operation ID for this endpoint.',
            )

        self._operation_ids.add(operation_id)
