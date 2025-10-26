import pytest
from django.http import HttpResponse

from django_modern_rest import path
from django_modern_rest.routing import _PrefixRoutePattern


def _simple_view() -> HttpResponse:
    raise NotImplementedError


@pytest.mark.parametrize(
    ('route', 'path_to_match', 'is_endpoint', 'should_match'),
    [
        ('users/', 'users/', True, True),
        ('users/', 'users/posts', True, False),
        ('users/', 'users/', False, True),
        ('users/', 'users/posts', False, True),
        ('users/<int:user_id>', 'users/123', False, True),
        ('users/<int:user_id>', 'users/abc', False, False),
        ('users/<int:user_id>', 'posts/123', False, False),
        ('<int:id>', '123', False, True),
        ('<int:id>', 'abc', False, False),
        (
            'api/v1/users/<int:user_id>/posts/<int:post_id>',
            'api/v1/users/123/posts/456',
            False,
            True,
        ),
        (
            'api/v1/users/<int:user_id>/posts/<int:post_id>',
            'api/v1/posts/123',
            False,
            False,
        ),
    ],
)
def test_prefix_route_pattern_matching(
    *,
    route: str,
    path_to_match: str,
    is_endpoint: bool,
    should_match: bool,
) -> None:
    """Ensures that `_PrefixRoutePattern` captures correct paths."""
    pattern = _PrefixRoutePattern(route, is_endpoint=is_endpoint)
    matched = pattern.match(path_to_match)
    if should_match:
        assert matched is not None
    else:
        assert matched is None


@pytest.mark.parametrize(
    ('route', 'matching_path', 'should_match'),
    [
        ('user/', 'user/', True),
        ('user/', 'users/', False),
        ('api/health/', 'api/health/', True),
        ('api/users/<int:user_id>', 'api/users/123', True),
        ('api/users/<int:user_id>', 'api/users/abc', False),
        ('api/<str:version>/users/<int:user_id>', 'api/v1/users/123', True),
        ('api/<str:version>/users/<int:user_id>', 'api/users/123', False),
    ],
)
def test_path_uses_prefix_pattern(
    *,
    route: str,
    matching_path: str,
    should_match: bool,
) -> None:
    """Ensures that `path` captures correct paths."""
    url_pattern = path(route, _simple_view)
    assert isinstance(url_pattern.pattern, _PrefixRoutePattern)
    matched = url_pattern.pattern.match(matching_path)
    if should_match:
        assert matched is not None
    else:
        assert matched is None
