import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, TypeAlias

from django.contrib.admindocs.views import simplify_regex
from django.urls import URLPattern, URLResolver

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects import PathItem
    from dmr.routing import Router


class SupportsPathItem(Protocol):
    """
    What the collector needs from a view to document it.

    Both a :class:`~dmr.controller.Controller` and a plain Django view
    adapted by :func:`~dmr.adapters.adapt_django_view` satisfy this.
    """

    @classmethod
    def get_path_item(
        cls,
        path: str,
        pattern: URLPattern,
        context: 'OpenAPIContext',
        router: 'Router',
    ) -> 'PathItem':
        """Describe the view as a single OpenAPI path item."""
        ...


_AnyPattern: TypeAlias = URLPattern | URLResolver
_PathControllerSpec: TypeAlias = tuple[str, URLPattern, type[SupportsPathItem]]


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str = '',
) -> _PathControllerSpec:
    path = _join_paths(base_path, str(url_pattern.pattern))
    controller = url_pattern.callback.view_class  # type: ignore[attr-defined]
    normalized = _normalize_path(path)
    return normalized, url_pattern, controller


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


def controller_mapping_collector(
    urls: Sequence[_AnyPattern],
    base_path: str = '',
) -> list[_PathControllerSpec]:
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
    controllers: list[_PathControllerSpec] = []

    for url in urls:
        if isinstance(url, URLPattern):
            controllers.append(_process_pattern(url, base_path))
        else:
            current_path = _join_paths(base_path, str(url.pattern))
            controllers.extend(
                controller_mapping_collector(url.url_patterns, current_path),
            )

    return controllers
