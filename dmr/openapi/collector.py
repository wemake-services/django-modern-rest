import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, TypeAlias

from django.contrib.admindocs.views import simplify_regex
from django.urls import URLPattern, URLResolver

from dmr.openapi.objects import PathItem

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_AnyPattern: TypeAlias = URLPattern | URLResolver
_PathControllerSpec: TypeAlias = (
    tuple[
        str,
        URLPattern,
        'Controller[BaseSerializer]',
    ]
    | tuple[
        str,
        PathItem | None,  # None used to disable external view from spec
        None,
    ]
)
_ExternalSpec: TypeAlias = tuple[URLPattern, PathItem | None]


def controller_mapping_collector(
    urls: Iterable[_AnyPattern],
    base_path: str,
) -> Iterable[_PathControllerSpec]:
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
    for url in urls:
        if isinstance(url, URLPattern):
            yield _process_pattern(url, base_path)
        else:
            current_path = _join_paths(base_path, str(url.pattern))
            yield from controller_mapping_collector(
                url.url_patterns,
                current_path,
            )


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str,
) -> _PathControllerSpec:
    path = _join_paths(base_path, str(url_pattern.pattern))
    normalized = _normalize_path(path)
    try:
        # Try the external url first, it is easier to detect:
        return normalized, url_pattern.callback.__dmr_external_openapi__, None  # type: ignore[attr-defined]
    except AttributeError:
        return normalized, url_pattern, url_pattern.callback.view_class  # type: ignore[attr-defined]


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
