from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.objects import (  # noqa: WPS235d
    Components,
    Info,
    OpenAPI,
    Paths,
)


class ConfigMerger:
    """Whatever must be replaced."""

    def __init__(self, context: OpenAPIContext) -> None:
        """Whatever must be replaced."""
        self.context = context

    def merge(
        self,
        paths: Paths,
        components: Components,
    ) -> OpenAPI:
        """Whatever must be replaced."""
        config = self.context.config
        return OpenAPI(
            info=Info(
                title=config.title,
                version=config.version,
                summary=config.summary,
                description=config.description,
                terms_of_service=config.terms_of_service,
                contact=config.contact,
                license=config.license,
            ),
            servers=config.servers,
            tags=config.tags,
            external_docs=config.external_docs,
            security=config.security,
            webhooks=config.webhooks,
            paths=paths,
            components=components,
            # TODO: Merge config.components and components
            # TODO: Merge config.webhooks and webhooks
            # TODO: Merge config.security and security
        )
