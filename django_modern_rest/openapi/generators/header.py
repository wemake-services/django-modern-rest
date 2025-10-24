from typing import TYPE_CHECKING

from django_modern_rest.headers import HeaderDescription
from django_modern_rest.openapi.objects.header import Header
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.types import Empty

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


class HeaderGenerator:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(
        self,
        headers: dict[str, HeaderDescription] | Empty,
    ) -> dict[str, Header | Reference] | None:
        """Whatever must be replaced."""
        if isinstance(headers, Empty):
            return None

        result_headers: dict[str, Header | Reference] = {}

        for header, description in headers.items():
            result_headers[header] = Header(required=description.required)

        return result_headers
