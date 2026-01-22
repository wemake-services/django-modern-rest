from typing import TYPE_CHECKING, TypedDict

from django_modern_rest.openapi.objects import PathItem

if TYPE_CHECKING:
    from django_modern_rest.openapi.collector import ControllerMapping
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.openapi.objects import Operation


# TODO: support openapi 3.2.0
class _PathItemKwargs(TypedDict, total=False):
    get: 'Operation'
    put: 'Operation'
    post: 'Operation'
    delete: 'Operation'
    options: 'Operation'
    head: 'Operation'
    patch: 'Operation'
    trace: 'Operation'


class PathItemGenerator:
    """
    Generator for OpenAPI PathItem objects.

    The PathItem Generator is responsible for creating PathItem objects
    that represent a single API endpoint with its possible HTTP operations.
    It takes a controller mapping and generates a PathItem containing all
    the operations (GET, POST, PUT, DELETE, etc.) defined for that endpoint.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the PathItem Generator."""
        self.context = context

    def generate(self, mapping: 'ControllerMapping') -> PathItem:
        """Generate an OpenAPI PathItem from a controller mapping."""
        kwargs: _PathItemKwargs = {}

        for method, endpoint in mapping.controller.api_endpoints.items():
            operation = self.context.operation_generator.generate(
                endpoint,
                mapping.path,
            )
            kwargs[method.lower()] = operation  # type: ignore[literal-required]

        return PathItem(**kwargs)
