from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects import (
    Components,
    Info,
    OpenAPI,
    Paths,
)

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


class ConfigMerger:
    """
    Merges OpenAPI configuration with generated paths and components.

    This class is responsible for combining the OpenAPI configuration
    from the context with the generated paths and components to create
    a complete OpenAPI specification object.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the merger with OpenAPI context."""
        self.context = context

    def merge(
        self,
        paths: Paths,
        components: Components,
    ) -> OpenAPI:
        """Merge paths and components with configuration."""
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
        )
