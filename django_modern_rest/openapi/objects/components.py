from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.callback import Callback
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.header import OpenAPIHeader
    from django_modern_rest.openapi.objects.link import Link
    from django_modern_rest.openapi.objects.parameter import Parameter
    from django_modern_rest.openapi.objects.path_item import PathItem
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.request_body import RequestBody
    from django_modern_rest.openapi.objects.response import OpenAPIResponse
    from django_modern_rest.openapi.objects.schema import Schema
    from django_modern_rest.openapi.objects.security_scheme import (
        SecurityScheme,
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class Components(BaseObject):
    """TODO: add docs."""

    schemas: 'dict[str, Schema]' = field(default_factory=dict)
    responses: 'dict[str, OpenAPIResponse | Reference] | None' = None
    parameters: 'dict[str, Parameter | Reference] | None' = None
    examples: 'dict[str, Example | Reference] | None' = None
    request_bodies: 'dict[str, RequestBody | Reference] | None' = None
    headers: 'dict[str, OpenAPIHeader | Reference] | None' = None
    security_schemes: 'dict[str, SecurityScheme | Reference] | None' = None
    links: 'dict[str, Link | Reference] | None' = None
    callbacks: 'dict[str, Callback | Reference] | None' = None
    path_items: 'dict[str, PathItem | Reference] | None' = None
