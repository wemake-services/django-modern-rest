from typing import Any, NamedTuple

from django.urls import URLPattern, URLResolver

from django_modern_rest.controller import Controller
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.routing import Router


class EndpointInfo(NamedTuple):
    """
    Information about an API endpoint for OpenAPI generation.

    This named tuple contains the essential information needed to generate
    OpenAPI specifications for a single API endpoint.

    Attributes:
        path: The URL path pattern for this endpoint (e.g., '/api/users/{id}/')
        endpoint: The Endpoint instance that handles this API endpoint
    """

    path: str
    endpoint: Endpoint


def _process_resolver(
    url_resolver: URLResolver,
    base_path: str = '',
) -> list[EndpointInfo]:
    endpoints: list[EndpointInfo] = []
    full_path = _join_paths(base_path, str(url_resolver.pattern))

    for url_pattern in url_resolver.url_patterns:
        if isinstance(url_pattern, URLPattern):
            pattern_endpoints = _process_pattern(url_pattern, full_path)
            endpoints.extend(pattern_endpoints)
        else:
            resolver_endpoints = _process_resolver(url_pattern, full_path)
            endpoints.extend(resolver_endpoints)

    return endpoints


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str = '',
) -> list[EndpointInfo]:
    endpoints: list[EndpointInfo] = []
    full_path = _join_paths(base_path, str(url_pattern.pattern))
    view = url_pattern.callback.view_class  # type: ignore[attr-defined]

    if hasattr(view, 'original_controllers'):
        for controller in view.original_controllers:
            endpoints.extend(_extract_endpoints(full_path, controller))
    elif hasattr(view, 'api_endpoints'):
        endpoints.extend(_extract_endpoints(full_path, view))

    return endpoints


def _extract_endpoints(
    path: str,
    controller: Controller[Any],
) -> list[EndpointInfo]:
    return [
        EndpointInfo(path=path, endpoint=endpoint)
        for endpoint in controller.api_endpoints.values()
    ]


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


def collect_endpoints(router: Router) -> list[EndpointInfo]:
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
    endpoints: list[EndpointInfo] = []

    for url in router.urls:
        if isinstance(url, URLPattern):
            pattern_endpoints = _process_pattern(url)
            endpoints.extend(pattern_endpoints)
        else:
            resolver_endpoints = _process_resolver(url)
            endpoints.extend(resolver_endpoints)

    return endpoints
