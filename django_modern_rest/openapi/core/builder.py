from typing import TYPE_CHECKING

from django_modern_rest.openapi.collector import controller_collector
from django_modern_rest.openapi.core.merger import ConfigMerger
from django_modern_rest.openapi.generators.component import ComponentGenerator
from django_modern_rest.openapi.generators.path_item import PathItemGenerator

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
        self._config_merger = ConfigMerger(context)
        self._path_generator = PathItemGenerator(context)
        self._component_generator = ComponentGenerator(context)

    def build(self, router: 'Router') -> 'OpenAPI':
        """Build complete OpenAPI specification from a router."""
        controller_registry = controller_collector(router)

        paths_items: Paths = {}
        for controller in controller_registry:
            path_item = self._path_generator.generate(controller)
            paths_items[controller.path] = path_item

        components = self._component_generator.generate(paths_items)
        return self._config_merger.merge(paths_items, components)
