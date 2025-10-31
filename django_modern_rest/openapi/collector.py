import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias

from django.contrib.admindocs.views import simplify_regex
from django.urls import URLPattern, URLResolver

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller

_AnyPattern: TypeAlias = URLPattern | URLResolver


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


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str = '',
) -> ControllerMapping:
    path = _join_paths(base_path, str(url_pattern.pattern))
    controller: Controller[Any] = url_pattern.callback.view_class  # type: ignore[attr-defined]
    normalized = _normalize_path(path)
    return ControllerMapping(path=normalized, controller=controller)


def _join_paths(base_path: str, pattern_path: str) -> str:
    if not pattern_path:
        return base_path
    base = base_path.rstrip('/')
    pattern = pattern_path.lstrip('/')
    return f'{base}/{pattern}' if base else pattern


def _normalize_path(path: str) -> str:
    path = simplify_regex(path)
    pattern = re.compile(r'<(?:(?P<converter>[^>:]+):)?(?P<parameter>\w+)>')
    return re.sub(pattern, r'{\g<parameter>}', path)


def controller_collector(
    urls: Sequence[_AnyPattern],
    base_path: str = '',
) -> list[ControllerMapping]:
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

    for url in urls:
        if isinstance(url, URLPattern):
            controllers.append(_process_pattern(url, base_path))
        else:
            current_path = _join_paths(base_path, str(url.pattern))
            controllers.extend(
                controller_collector(url.url_patterns, current_path),
            )

    return controllers
