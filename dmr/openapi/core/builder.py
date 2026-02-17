import dataclasses
from typing import TYPE_CHECKING

from django_modern_rest.openapi.collector import controller_collector

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.openapi.objects import OpenAPI, Paths
    from django_modern_rest.routing import Router


@dataclasses.dataclass(frozen=True, slots=True)
class OpenApiBuilder:
    """
    Builds OpenAPI specification.

    This class orchestrates the process of generating a complete OpenAPI
    specification by collecting controllers from the router, generating path
    items for each controller, extracting shared components, and merging
    everything together with the configuration.
    """

    _context: 'OpenAPIContext'

    def __call__(self, router: 'Router') -> 'OpenAPI':
        """Build complete OpenAPI specification from a router."""
        paths_items: Paths = {}

        for controller in controller_collector(router.urls):
            path_item = self._context.generators.path_item(controller)
            paths_items[controller.path] = path_item

        components = self._context.generators.component(paths_items)
        return self._context.config_merger(paths_items, components)
