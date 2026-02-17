from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from dmr.openapi.objects.callback import Callback
    from dmr.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )
    from dmr.openapi.objects.parameter import Parameter
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.request_body import RequestBody
    from dmr.openapi.objects.responses import Responses
    from dmr.openapi.objects.security_requirement import (
        SecurityRequirement,
    )
    from dmr.openapi.objects.server import Server


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Operation:
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
