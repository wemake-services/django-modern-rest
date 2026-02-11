from typing import TYPE_CHECKING

from django_modern_rest.openapi.collector import controller_collector

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.openapi.objects import OpenAPI, Paths
    from django_modern_rest.routing import Router


class OpenApiBuilder:
    """
    Builds OpenAPI specification.

    This class orchestrates the process of generating a complete OpenAPI
    specification by collecting controllers from the router, generating path
    items for each controller, extracting shared components, and merging
    everything together with the configuration.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the builder with OpenAPI context."""
        self.context = context

    def build(self, router: 'Router') -> 'OpenAPI':
        """Build complete OpenAPI specification from a router."""
        paths_items: Paths = {}

        for controller in controller_collector(router.urls):
            path_item = self.context.generators.path_item(controller)
            paths_items[controller.path] = path_item

        components = self.context.generators.component(paths_items)
        return self.context.config_merger.merge(paths_items, components)
