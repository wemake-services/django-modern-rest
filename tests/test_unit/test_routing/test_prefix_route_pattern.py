import pytest
from django.http import HttpRequest, HttpResponse
from django.urls import include

from dmr.routing import _PrefixRoutePattern, path


def _simple_view(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


@pytest.mark.parametrize(
    (
        'prefix',
        'nested',
        'input_path',
        'expected_remaining',
        'expected_capture',
    ),
    [
        ('users/', '', 'users/', '', {}),
        ('users/', '', 'users/posts/', 'posts/', {}),
        ('users/', '<int:post_id>/', 'users/123/', '123/', {}),
        ('users/', 'posts/', 'users/posts/', 'posts/', {}),
        ('users/', 'posts/', 'users/posts/123/', 'posts/123/', {}),
        ('api/', 'v1/', 'api/v1/users/', 'v1/users/', {}),
        ('api/<str:version>/', '', 'api/v1/', '', {'version': 'v1'}),
        (
            'api/<str:version>/',
            'users/',
            'api/v1/users/',
            'users/',
            {'version': 'v1'},
        ),
        ('<int:id>/', '', '123/', '', {'id': 123}),
        ('<int:id>/', 'posts/', '123/posts/', 'posts/', {'id': 123}),
        (
            'api/v1/users/<int:user_id>/',
            'posts/<int:post_id>/',
            'api/v1/users/123/posts/456/',
            'posts/456/',
            {'user_id': 123},
        ),
        (
            'users/<int:user_id>/',
            'posts/<int:post_id>/',
            'users/123/posts/456/',
            'posts/456/',
            {'user_id': 123},
        ),
        ('users/', 'posts/', 'posts/123/', None, None),
        ('api/<int:version>/', 'users/', 'api/v1/users/', None, None),
        ('users/<int:user_id>/', '', 'users/abc/', None, None),
        ('<int:id>/', '', 'abc/', None, None),
        ('api/<int:version>/', 'users/', 'api/invalid/users/', None, None),
        ('api/<int:version>/', '', 'other/path/', None, None),
    ],
)
def test_path(
    *,
    prefix: str,
    nested: str,
    input_path: str,
    expected_remaining: str | None,
    expected_capture: dict[str, int | str] | None,
) -> None:
    """Ensures that prefix-optimized `path` works."""
    url_pattern = path(prefix, include(([path(nested, _simple_view)], 'app')))
    assert isinstance(url_pattern.pattern, _PrefixRoutePattern)
    matched = url_pattern.pattern.match(input_path)
    if expected_capture is None:
        assert matched is None
    else:
        assert matched is not None
        remaining_path, args, kwargs = matched
        assert remaining_path == expected_remaining
        assert args == ()
        assert kwargs == expected_capture
