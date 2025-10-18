from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.callback import Callback
    from django_modern_rest.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )
    from django_modern_rest.openapi.objects.parameter import Parameter
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.request_body import RequestBody
    from django_modern_rest.openapi.objects.responses import Responses
    from django_modern_rest.openapi.objects.security_requirement import (
        SecurityRequirement,
    )
    from django_modern_rest.openapi.objects.server import Server


@dataclass(frozen=True, kw_only=True, slots=True)
class Operation(BaseObject):
    """Describes a single API operation on a path."""

    tags: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    external_docs: 'ExternalDocumentation | None' = None
    operation_id: str | None = None
    parameters: 'list[Parameter | Reference] | None' = None
    request_body: 'RequestBody | Reference | None' = None
    responses: 'Responses | None' = None
    callbacks: 'dict[str, Callback | Reference] | None' = None
    deprecated: bool = False
    security: 'list[SecurityRequirement] | None' = None
    servers: 'list[Server] | None' = None
