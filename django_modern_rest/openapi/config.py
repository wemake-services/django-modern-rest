from dataclasses import dataclass

from django_modern_rest.openapi.objects import (  # noqa: WPS235d
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


@dataclass(slots=True, frozen=True, kw_only=True)
class OpenAPIConfig:
    """
    Configuration class for customizing OpenAPI specification metadata.

    This class provides a way to configure various aspects of the OpenAPI
    specification that will be generated for your API documentation. It allows
    you to customize the API information, contact details, licensing, security
    requirements, and other metadata that appears in the generated OpenAPI spec.
    """

    title: str
    version: str

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
    use_handler_docstrings: bool = False
    webhooks: dict[str, PathItem | Reference] | None = None
