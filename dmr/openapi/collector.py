import re
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Final, TypeAlias

from django.urls import URLPattern, URLResolver
from django.urls.resolvers import RegexPattern, RoutePattern

from dmr.openapi.objects import PathItem

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_AnyPattern: TypeAlias = URLPattern | URLResolver
_BasePattern: TypeAlias = RoutePattern | RegexPattern
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

_PATH_PATTERN: Final = re.compile(
    r'<(?:(?P<converter>[^>:]+):)?(?P<parameter>\w+)>',
)


def controller_mapping_collector(
    urls: Iterable[_AnyPattern],
    base_path: str,
    parent_patterns: Sequence[_BasePattern] = (),
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
    if not parent_patterns:
        parent_patterns = _prefix_patterns(base_path)

    for url in urls:
        if isinstance(url, URLPattern):
            yield _process_pattern(url, base_path, parent_patterns)
        else:
            current_path = _join_paths(base_path, str(url.pattern))
            yield from controller_mapping_collector(
                url.url_patterns,
                current_path,
                (*parent_patterns, url.pattern),
            )


def collect_normalized_paths(
    urls: Iterable[_AnyPattern],
    *,
    original_prefix: str,
    new_prefix: str,
) -> Iterable[tuple[str, str]]:
    """Collects all normalized paths from a router."""
    for url in urls:
        original_path = _join_paths(original_prefix, str(url.pattern))
        if isinstance(url, URLPattern):
            yield original_path, _join_paths(new_prefix, original_path)
        else:
            yield from collect_normalized_paths(
                url.url_patterns,
                original_prefix=_join_paths(original_prefix, str(url.pattern)),
                new_prefix=new_prefix,
            )


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str,
    parent_patterns: Sequence[_BasePattern] = (),
) -> _PathControllerSpec:
    normalized = _join_paths(base_path, str(url_pattern.pattern))
    try:
        # Try the external url first, it is easier to detect:
        return normalized, url_pattern.callback.__dmr_external_openapi__, None  # type: ignore[attr-defined]
    except AttributeError:
        pattern = _merge_parent_patterns(url_pattern, parent_patterns)
        return normalized, pattern, url_pattern.callback.view_class  # type: ignore[attr-defined]


def _merge_parent_patterns(
    url_pattern: URLPattern,
    parent_patterns: Sequence[_BasePattern],
) -> URLPattern:
    """Merge parent resolver patterns into the child URL pattern.

    When URL patterns are nested (e.g., a ``URLResolver`` wrapping
    a ``URLPattern``), the child pattern only contains its own
    converters. This function creates a new ``URLPattern`` whose
    pattern includes converters from all parent resolvers
    so the OpenAPI generator can emit every path parameter.
    """
    if not parent_patterns:
        return url_pattern

    all_route = all(isinstance(pat, RoutePattern) for pat in parent_patterns)

    if all_route and isinstance(url_pattern.pattern, RoutePattern):
        parts = [
            pat._route  # noqa: SLF001, WPS437
            for pat in parent_patterns
            if isinstance(pat, RoutePattern)
        ]
        parts.append(url_pattern.pattern._route)  # noqa: SLF001, WPS437
        combined_route = _join_raw_routes(*parts)
        return URLPattern(RoutePattern(combined_route), url_pattern.callback)

    # Mixed or regex-only: combine everything as regex.
    regex_parts = [
        pat.regex.pattern.lstrip('^').rstrip('\\Z') for pat in parent_patterns
    ]
    child_regex = url_pattern.pattern.regex.pattern.lstrip('^')
    regex_parts.append(child_regex)
    combined_regex = _join_raw_routes(*regex_parts)
    return URLPattern(
        RegexPattern(f'^{combined_regex}'),
        url_pattern.callback,
    )


def _prefix_patterns(base_path: str) -> tuple[_BasePattern, ...]:
    """Create parent patterns from a Router prefix if it has converters."""
    if _PATH_PATTERN.search(base_path):
        return (RoutePattern(base_path),)
    return ()


def _join_raw_routes(*parts: str) -> str:
    """Join raw Django route strings preserving converter syntax."""
    result = ''
    for part in parts:
        if not part:
            continue
        if not result:
            result = part
        else:
            result = f'{result.rstrip("/")}/{part.lstrip("/")}'
    return result


def _join_paths(base_path: str, pattern_path: str) -> str:
    if not pattern_path:
        return _normalize_path(base_path)
    base = base_path.rstrip('/')
    pattern = pattern_path.lstrip('/')
    return _normalize_path(f'{base}/{pattern}' if base else pattern)


def _normalize_path(path: str) -> str:
    # Heavy import:
    from django.contrib.admindocs.views import simplify_regex  # noqa: PLC0415

    return _PATH_PATTERN.sub(r'{\g<parameter>}', simplify_regex(path))
