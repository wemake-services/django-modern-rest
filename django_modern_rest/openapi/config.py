from dataclasses import dataclass

from django_modern_rest.openapi.objects import (  # noqa: WPS235
    Components,
    Contact,
    ExternalDocumentation,
    Info,
    License,
    OpenAPI,
    PathItem,
    Reference,
    SecurityRequirement,
    Server,
    Tag,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class OpenAPIConfig:
    """Configuration for OpenAPI."""

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

    def to_openapi(self) -> OpenAPI:
        """TODO: add docs."""
        return OpenAPI(
            external_docs=self.external_docs,
            security=self.security,
            servers=self.servers,
            tags=self.tags,
            webhooks=self.webhooks,
            info=Info(
                title=self.title,
                version=self.version,
                description=self.description,
                contact=self.contact,
                license=self.license,
                summary=self.summary,
                terms_of_service=self.terms_of_service,
            ),
            paths={},
        )
