from typing import TYPE_CHECKING

from django_modern_rest.openapi.collector import (
    ControllerCollector,
    controller_collector,
)
from django_modern_rest.openapi.core.merger import ConfigMerger
from django_modern_rest.openapi.generators.component import ComponentGenerator
from django_modern_rest.openapi.generators.path_item import PathItemGenerator
from django_modern_rest.openapi.objects import OpenAPI, Paths
from django_modern_rest.routing import Router

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


class OpenApiBuilder:
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

        self._config_merger = ConfigMerger(context)
        self._path_generator = PathItemGenerator(context)
        self._component_generator = ComponentGenerator(context)
        self._controller_collector: ControllerCollector = controller_collector

    def build(self, router: Router) -> OpenAPI:
        """Whatever must be replaced."""
        controller_registry = self._controller_collector(router)

        paths_items: Paths = {}
        for controller in controller_registry:
            path_item = self._path_generator.generate(controller)
            paths_items[controller.path] = path_item

        components = self._component_generator.generate(paths_items)
        return self._config_merger.merge(
            self.context.config,
            paths_items,
            components,
        )
