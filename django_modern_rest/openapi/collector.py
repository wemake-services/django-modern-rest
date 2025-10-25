from typing import TYPE_CHECKING, Any, NamedTuple

from django.contrib.admindocs.views import simplify_regex
from django.urls import URLPattern, URLResolver

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.routing import Router


class ControllerMapping(NamedTuple):
    """
    Information about an API controller for OpenAPI generation.

    This named tuple contains the essential information needed to generate
    OpenAPI specifications for a single API controller.

    Attributes:
        path: The URL path pattern for this controller (e.g., '/users/{id}/')
        controller: The Controller instance that handles this API controller
    """

    path: str
    controller: 'Controller[Any]'


def _process_resolver(
    url_resolver: URLResolver,
    base_path: str = '',
) -> list[ControllerMapping]:
    controllers: list[ControllerMapping] = []
    full_path = _join_paths(base_path, str(url_resolver.pattern))

    for url_pattern in url_resolver.url_patterns:
        if isinstance(url_pattern, URLPattern):
            controllers.append(_process_pattern(url_pattern, full_path))
        else:
            controllers.extend(_process_resolver(url_pattern, full_path))

    return controllers


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str = '',
) -> ControllerMapping:
    path = _join_paths(base_path, str(url_pattern.pattern))
    controller: Controller[Any] = url_pattern.callback.view_class  # type: ignore[attr-defined]
    # TODO: path normalization must be configurable (simplify_regex)
    return ControllerMapping(path=simplify_regex(path), controller=controller)


def _join_paths(base_path: str, pattern_path: str) -> str:
    if not pattern_path:
        return base_path
    base = base_path.rstrip('/')
    pattern = pattern_path.lstrip('/')
    return f'{base}/{pattern}' if base else pattern


def controller_collector(router: 'Router') -> list[ControllerMapping]:
    """
    Collect all API controllers from a router for OpenAPI generation.

    This is the main entry point for collecting controllers information from
    a Router instance. It processes all URL patterns and resolvers in the
    router to find all API controllers that can be documented in an OpenAPI
    specification.

    The function traverses the entire URL configuration tree, handling both
    direct URL patterns and nested URL resolvers, to build a comprehensive
    list of all available API controllers.
    """
    controllers: list[ControllerMapping] = []

    for url in router.urls:
        if isinstance(url, URLPattern):
            controllers.append(_process_pattern(url))
        else:
            controllers.extend(_process_resolver(url))

    return controllers
