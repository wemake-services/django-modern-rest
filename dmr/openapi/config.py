from dataclasses import dataclass
from typing import Literal, TypeAlias, cast

from dmr.openapi.objects import (  # noqa: WPS235
    Components,
    Contact,
    ExternalDocumentation,
    License,
    PathItem,
    Reference,
    SecurityRequirement,
    Server,
    Tag,
)

_SupportedOpenAPIVersions: TypeAlias = Literal['3.0.0', '3.1.0', '3.2.0']


@dataclass(slots=True, frozen=True, kw_only=True)
class OpenAPIConfig:
    """
    Configuration class for customizing OpenAPI specification metadata.

    This class provides a way to configure various aspects of the OpenAPI
    specification that will be generated for your API documentation. It allows
    you to customize the API information, contact details, licensing, security
    requirements, and other metadata that appears in the generated OpenAPI spec.

    Attributes:
        title: Human-readable title of the API,
            shown in the generated documentation.
        version: Version of your API
            (your application's own version, not the OpenAPI spec version).
        openapi_version: Version of the OpenAPI specification to target.
            Defaults to ``'3.1.0'``.
        summary: Short, one-line summary of the API.
        description: Longer description of the API. May use CommonMark syntax.
        terms_of_service: URL to the terms of service for the API.
        contact: Contact information for the exposed API.
        external_docs: Link to additional external documentation.
        security: Global security requirements applied across the API.
            Each entry may be overridden per operation.
        license: License information for the exposed API.
        components: Reusable components (schemas, responses, parameters, etc.)
            to include in the spec.
        servers: Connectivity information for the target servers.
        tags: Metadata tags used to group operations in the documentation.
        webhooks: Webhook definitions that may be initiated by the API,
            keyed by name.
    """

    title: str
    version: str
    openapi_version: _SupportedOpenAPIVersions = '3.1.0'

    summary: str | None = None
    description: str | None = None
    terms_of_service: str | None = None
    contact: Contact | None = None
    external_docs: ExternalDocumentation | None = None
    security: list[SecurityRequirement] | None = None
    license: License | None = None
    components: Components | list[Components] | None = None
    servers: list[Server] | None = None
    tags: list[Tag] | None = None
    webhooks: dict[str, PathItem | Reference] | None = None

    @property
    def openapi_version_info(self) -> tuple[int, int, int]:
        """
        Returns the parsed OpenAPI version.

        .. versionadded:: 0.8.0
        """
        return cast(
            'tuple[int, int, int]',
            tuple(map(int, self.openapi_version.split('.'))),
        )
