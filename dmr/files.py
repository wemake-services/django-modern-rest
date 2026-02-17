import dataclasses
from typing import final

from django_modern_rest.openapi.objects.enums import (
    OpenAPIFormat,
    OpenAPIType,
)
from django_modern_rest.openapi.objects.schema import Schema


@final
@dataclasses.dataclass(slots=True, frozen=True)
class FileBody:
    """Special type that indicates that response returns a file body."""

    @classmethod
    def schema(cls) -> Schema:
        """Returns the openapi schema that this object represents."""
        return Schema(format=OpenAPIFormat.BINARY, type=OpenAPIType.STRING)
