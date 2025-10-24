from typing import override

from django_modern_rest.openapi.processors.base import BaseProcessor


class MsgspecProcessor(BaseProcessor):
    """Whatever must be replaced."""

    @override
    def is_supports(self) -> bool:
        """Whatever must be replaced."""

    @override
    def process(self) -> ...:
        """Whatever must be replaced."""
