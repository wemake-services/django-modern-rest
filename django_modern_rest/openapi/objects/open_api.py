from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final

from django_modern_rest.openapi.objects.components import Components

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )
    from django_modern_rest.openapi.objects.info import Info
    from django_modern_rest.openapi.objects.path_item import PathItem
    from django_modern_rest.openapi.objects.paths import Paths
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.security_requirement import (
        SecurityRequirement,
    )
    from django_modern_rest.openapi.objects.server import Server
    from django_modern_rest.openapi.objects.tag import Tag

_OPENAPI_VERSION: Final = '3.1.0'


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAPI:
    """This is the root object of the OpenAPI document."""

    openapi: str = _OPENAPI_VERSION

    info: 'Info'
    json_schema_dialect: str | None = None
    servers: 'list[Server] | None' = None
    paths: 'Paths | None' = None
    webhooks: 'dict[str, PathItem | Reference] | None' = None
    components: 'Components | None' = None
    security: 'list[SecurityRequirement] | None' = None
    tags: 'list[Tag] | None' = None
    external_docs: 'ExternalDocumentation | None' = None
