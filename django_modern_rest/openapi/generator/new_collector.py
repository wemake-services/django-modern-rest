from typing import Any, NamedTuple

from django.urls import URLPattern, URLResolver

from django_modern_rest.controller import Controller
from django_modern_rest.routing import Router


class ControllerInfo(NamedTuple):
    """
    Information about an API endpoint for OpenAPI generation.

    This named tuple contains the essential information needed to generate
    OpenAPI specifications for a single API endpoint.

    Attributes:
        path: The URL path pattern for this endpoint (e.g., '/api/users/{id}/')
        endpoint: The Endpoint instance that handles this API endpoint
    """

    path: str
    controller: Controller[Any]


def _process_resolver(
    url_resolver: URLResolver,
    base_path: str = '',
) -> list[ControllerInfo]:
    controllers: list[ControllerInfo] = []
    full_path = _join_paths(base_path, str(url_resolver.pattern))

    for url_pattern in url_resolver.url_patterns:
        if isinstance(url_pattern, URLPattern):
            pattern_controllers = _process_pattern(url_pattern, full_path)
            controllers.append(pattern_controllers)
        else:
            resolver_controllers = _process_resolver(url_pattern, full_path)
            controllers.extend(resolver_controllers)

    return controllers


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str = '',
) -> ControllerInfo:
    path = _join_paths(base_path, str(url_pattern.pattern))
    controller = url_pattern.callback.view_class  # type: ignore[attr-defined]
    return ControllerInfo(path=path, controller=controller)


def _join_paths(base_path: str, pattern_path: str) -> str:
    if not base_path:
        return pattern_path
    if not pattern_path:
        return base_path

    pattern_path = pattern_path.lstrip('/')

    if pattern_path:
        base_path = base_path.rstrip('/')
        return f'{base_path}/{pattern_path}'
    return base_path


def collect_controllers(router: Router) -> list[ControllerInfo]:
    """
    Collect all API endpoints from a router for OpenAPI generation.

    This is the main entry point for collecting endpoint information from
    a Router instance. It processes all URL patterns and resolvers in the
    router to find all API endpoints that can be documented in an OpenAPI
    specification.

    The function traverses the entire URL configuration tree, handling both
    direct URL patterns and nested URL resolvers, to build a comprehensive
    list of all available API endpoints.

    Args:
        router: The Router instance containing URL patterns to process

    Returns:
        A list of EndpointInfo objects representing all API endpoints
        found in the router's URL configuration
    """
    controllers: list[ControllerInfo] = []

    for url in router.urls:
        if isinstance(url, URLPattern):
            pattern_endpoints = _process_pattern(url)
            controllers.append(pattern_endpoints)
        else:
            resolver_endpoints = _process_resolver(url)
            controllers.extend(resolver_endpoints)

    return controllers
