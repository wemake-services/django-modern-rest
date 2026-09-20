import dataclasses
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Final, TypeAlias, final

from django.urls import URLPattern, URLResolver
from django.urls.resolvers import RegexPattern, RoutePattern

from dmr.openapi.objects import PathItem

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_AnyPattern: TypeAlias = URLPattern | URLResolver
_RouteMetadata: TypeAlias = (
    tuple['InternalRouteMetadata', type['Controller[BaseSerializer]']]
    | tuple['ExternalRouteMetadata', None]
)

_PATH_PATTERN: Final = re.compile(
    r'<(?:(?P<converter>[^>:]+):)?(?P<parameter>\w+)>',
)


def controller_mapping_collector(
    urls: Iterable[_AnyPattern],
    base_path: str,
) -> Iterable[_RouteMetadata]:
    """
    Collect all API controllers from a router for OpenAPI generation.

    This is the main entry point for collecting controllers information from
    a Router instance. It processes all URL patterns and resolvers in the
    router to find all API controllers that can be documented in an OpenAPI
    specification.

    The function traverses the entire URL configuration tree, handling both
    direct URL patterns and nested URL resolvers, to build a comprehensive
    list of all available API controllers.

    Args:
        urls: Iterable of URLs that we added to the ``Router``.
        base_path: Common prefix that these URLs have. In a Django format.

    """
    for url in urls:
        if isinstance(url, URLPattern):
            yield _process_pattern(url, base_path)
        else:
            yield from controller_mapping_collector(
                url.url_patterns,
                _join_paths(base_path, str(url.pattern), normalize=False),
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


@dataclasses.dataclass(frozen=True, slots=True)
class _BaseRouteMetadata:
    path: str
    is_regex: bool

    _normalized_path: str | None = dataclasses.field(init=False, default=None)

    @property
    def normalized_path(self) -> str:
        # We cache this one, because it is quite commonly used and is heavy.
        if self._normalized_path is not None:
            return self._normalized_path
        normalized = _normalize_path(self.path)
        object.__setattr__(self, '_normalized_path', normalized)  # noqa: PLC2801
        return normalized

    def regex(self) -> re.Pattern[str]:
        assert self.is_regex, "Can't get regex from non-regex route metadata"  # noqa: S101
        return RegexPattern(self.path, is_endpoint=True).regex

    def converters(self) -> dict[str, Any]:
        assert not self.is_regex, (  # noqa: S101
            "Can't get converters from regex route metadata"
        )
        return RoutePattern(self.path, is_endpoint=True).converters


@final
@dataclasses.dataclass(frozen=True, slots=True)
class InternalRouteMetadata(_BaseRouteMetadata):
    """
    Represents the metadata we need to create OpenAPI path parameters.

    Used for regular DMR views and URLs.
    It is not used for routing and is only needed for metadata.

    .. versionadded:: 0.16.0
    """


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ExternalRouteMetadata(_BaseRouteMetadata):
    """
    Represents the metadata we need to reuse external OpenAPI parameters.

    Used for external views and URLs.
    It is not used for routing and is only needed for metadata.

    .. versionadded:: 0.16.0
    """

    #: Optional path item, if set to `None`, it will be hidden from the spec.
    openapi: PathItem | None


def _process_pattern(
    url_pattern: URLPattern,
    base_path: str,
) -> _RouteMetadata:
    joined = _join_paths(base_path, str(url_pattern.pattern), normalize=False)

    try:
        # Try the external URL first, it is easier to detect:
        return (
            ExternalRouteMetadata(
                joined,
                is_regex=False,
                openapi=url_pattern.callback.__dmr_external_openapi__,  # type: ignore[attr-defined]
            ),
            None,
        )
    except AttributeError:
        # Regular, non-external URL:
        return (
            InternalRouteMetadata(
                joined,
                is_regex=isinstance(url_pattern.pattern, RegexPattern),
            ),
            url_pattern.callback.view_class,  # type: ignore[attr-defined]
        )


def _join_paths(
    base_path: str,
    pattern_path: str,
    *,
    normalize: bool = True,
) -> str:
    if not pattern_path:
        return _normalize_path(base_path) if normalize else base_path
    base = base_path.rstrip('/')
    pattern = pattern_path.lstrip('/')
    joined = f'{base}/{pattern}' if base else pattern
    return _normalize_path(joined) if normalize else joined


def _normalize_path(path: str) -> str:
    """
    Normalize Django path into OpenAPI path.

    Here's the example of how it works:

    .. code-block:: python

        >>> _normalize_path('/api/users/<int:pk>/posts/<int:post>')
        '/api/users/{pk}/posts/{post}'

    .. versionadded:: 0.16.0
    """
    # Heavy import:
    from django.contrib.admindocs.views import simplify_regex  # noqa: PLC0415

    return _PATH_PATTERN.sub(r'{\g<parameter>}', simplify_regex(path))
