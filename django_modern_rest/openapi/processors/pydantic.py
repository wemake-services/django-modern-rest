from typing import Any, override

from django_modern_rest.openapi.processors.base import BaseProcessor


class PydanticProcessor(BaseProcessor):
    """Whatever must be replaced."""

    @override
    def is_supports(self) -> bool:
        """Whatever must be replaced."""
        raise NotImplementedError

    @override
    def process(self) -> Any:
        """Whatever must be replaced."""
        raise NotImplementedError
