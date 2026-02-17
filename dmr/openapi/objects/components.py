from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from dmr.openapi.objects.callback import Callback
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.header import Header
    from dmr.openapi.objects.link import Link
    from dmr.openapi.objects.parameter import Parameter
    from dmr.openapi.objects.path_item import PathItem
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.request_body import RequestBody
    from dmr.openapi.objects.response import Response
    from dmr.openapi.objects.schema import Schema
    from dmr.openapi.objects.security_scheme import (
        SecurityScheme,
    )


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Components:
    """
    Holds a set of reusable objects for different aspects of the OAS.

    All objects defined within the components object will have no effect
    on the API unless they are explicitly referenced from properties
    outside the components object.
    """

    schemas: 'dict[str, Schema] | None' = None
    responses: 'dict[str, Response | Reference] | None' = None
    parameters: 'dict[str, Parameter | Reference] | None' = None
    examples: 'dict[str, Example | Reference] | None' = None
    request_bodies: 'dict[str, RequestBody | Reference] | None' = None
    headers: 'dict[str, Header | Reference] | None' = None
    security_schemes: 'dict[str, SecurityScheme | Reference] | None' = None
    links: 'dict[str, Link | Reference] | None' = None
    callbacks: 'dict[str, Callback | Reference] | None' = None
    path_items: 'dict[str, PathItem | Reference] | None' = None
