from typing import TYPE_CHECKING, TypedDict

from django_modern_rest.openapi.objects import PathItem

if TYPE_CHECKING:
    from django_modern_rest.openapi.collector import ControllerMapping
    from django_modern_rest.openapi.core.context import OpenAPIContext
    from django_modern_rest.openapi.objects import Operation


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
    """Whatever must be replaced."""

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Whatever must be replaced."""
        self.context = context

    def generate(self, mapping: 'ControllerMapping') -> PathItem:
        """Whatever must be replaced."""
        kwargs: _PathItemKwargs = {}

        for method, endpoint in mapping.controller.api_endpoints.items():
            operation = self.context.operation_generator.generate(endpoint)
            kwargs[method.lower()] = operation  # type: ignore[literal-required]

        return PathItem(**kwargs)
