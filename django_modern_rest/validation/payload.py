import dataclasses
from collections.abc import Mapping, Set
from http import HTTPStatus
from typing import TYPE_CHECKING, TypeAlias

from django_modern_rest.cookies import NewCookie
from django_modern_rest.errors import AsyncErrorHandlerT, SyncErrorHandlerT
from django_modern_rest.headers import NewHeader
from django_modern_rest.response import ResponseSpec
from django_modern_rest.settings import HttpSpec

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Reference,
        SecurityRequirement,
        Server,
    )


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True, init=False)
class _BasePayload:
    # OpenAPI stuff:
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    operation_id: str | None = None
    deprecated: bool = False
    security: list['SecurityRequirement'] | None = None
    external_docs: 'ExternalDocumentation | None' = None
    callbacks: 'dict[str, Callback | Reference] | None' = None
    servers: list['Server'] | None = None

    # Common fields:
    validate_responses: bool | None = None
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | None = None
    allow_custom_http_methods: bool = False
    no_validate_http_spec: Set[HttpSpec] | None = None


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ValidateEndpointPayload(_BasePayload):
    """Payload created by ``@validate``."""

    responses: list[ResponseSpec]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModifyEndpointPayload(_BasePayload):
    """Payload created by ``@modify``."""

    status_code: HTTPStatus | None
    headers: Mapping[str, NewHeader] | None
    cookies: Mapping[str, NewCookie] | None
    responses: list[ResponseSpec] | None


#: Alias for different payload types:
PayloadT: TypeAlias = ValidateEndpointPayload | ModifyEndpointPayload | None
