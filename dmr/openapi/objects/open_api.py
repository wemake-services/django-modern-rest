from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final

if TYPE_CHECKING:
    from dmr.openapi.objects.components import Components
    from dmr.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )
    from dmr.openapi.objects.info import Info
    from dmr.openapi.objects.path_item import PathItem
    from dmr.openapi.objects.paths import Paths
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.security_requirement import (
        SecurityRequirement,
    )
    from dmr.openapi.objects.server import Server
    from dmr.openapi.objects.tag import Tag

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
