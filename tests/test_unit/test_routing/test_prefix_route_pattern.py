import pytest
from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, include
from django.utils import translation
from django.utils.functional import lazy

from dmr.internal.routing import PrefixRoutePattern, _RouteMatch
from dmr.internal.types import StrOrPromise
from dmr.routing import Router, path


def _simple_view(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


def _lazy_route(english: str, russian: str) -> StrOrPromise:
    def translate() -> str:
        if translation.get_language() == 'ru':
            return russian
        return english

    return lazy(translate, str)()


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
    """Ensures that prefix-optimized ``path`` works."""
    url_pattern = path(prefix, include(([path(nested, _simple_view)], 'app')))
    assert isinstance(url_pattern.pattern, PrefixRoutePattern)
    matched = url_pattern.pattern.match(input_path)
    if expected_capture is None:
        assert matched is None
    else:
        assert matched is not None
        remaining_path, args, kwargs = matched
        assert remaining_path == expected_remaining
        assert args == ()
        assert kwargs == expected_capture


def test_path_exact_match() -> None:
    """Ensures that static ``path`` matches exactly."""
    url_pattern = path('users/', _simple_view)
    assert isinstance(url_pattern.pattern, PrefixRoutePattern)

    matched = url_pattern.pattern.match('users/')
    assert matched == ('', (), {})


@pytest.mark.parametrize(
    ('language', 'input_path', 'expected'),
    [
        ('en', 'books/1/', ('', (), {'pk': 1})),
        ('en', 'knigi/1/', None),
        ('ru', 'knigi/1/', ('', (), {'pk': 1})),
        ('ru', 'books/1/', None),
    ],
)
def test_lazy_path_with_param(
    *,
    language: str,
    input_path: str,
    expected: _RouteMatch | None,
) -> None:
    """Ensures that lazy parameterized ``path`` resolves per language."""
    url_pattern = path(
        _lazy_route('books/<int:pk>/', 'knigi/<int:pk>/'),
        _simple_view,
    )
    assert isinstance(url_pattern.pattern, PrefixRoutePattern)

    with translation.override(language):
        assert url_pattern.pattern.match(input_path) == expected


@pytest.mark.parametrize(
    ('language', 'input_path', 'expected'),
    [
        ('en', 'shop/shelf/', ('shelf/', (), {})),
        ('en', 'magazin/shelf/', None),
        ('ru', 'magazin/shelf/', ('shelf/', (), {})),
        ('ru', 'shop/shelf/', None),
    ],
)
def test_lazy_path_with_include(
    *,
    language: str,
    input_path: str,
    expected: _RouteMatch | None,
) -> None:
    """Ensures that lazy include ``path`` resolves per language."""
    url_pattern = path(
        _lazy_route('shop/', 'magazin/'),
        include([path('shelf/', _simple_view)]),
    )
    assert isinstance(url_pattern.pattern, PrefixRoutePattern)

    with translation.override(language):
        assert url_pattern.pattern.match(input_path) == expected


@pytest.mark.parametrize(
    ('language', 'input_path', 'expected'),
    [
        ('en', 'shelf/', ('', (), {})),
        ('en', 'polka/', None),
        ('ru', 'polka/', ('', (), {})),
        ('ru', 'shelf/', None),
    ],
)
def test_lazy_static_endpoint_path(
    *,
    language: str,
    input_path: str,
    expected: _RouteMatch | None,
) -> None:
    """Ensures that lazy static endpoint ``path`` resolves per language."""
    url_pattern = path(_lazy_route('shelf/', 'polka/'), _simple_view)
    assert isinstance(url_pattern.pattern, PrefixRoutePattern)

    with translation.override(language):
        assert url_pattern.pattern.match(input_path) == expected


def test_lazy_routes_resolve_through_router() -> None:
    """Ensures that translated routes resolve through ``Router``."""
    router = Router(
        'api/',
        [
            path(
                _lazy_route('books/<int:pk>/', 'knigi/<int:pk>/'),
                _simple_view,
                name='book',
            ),
            path(
                _lazy_route('shop/', 'magazin/'),
                include([path('shelf/', _simple_view, name='shelf')]),
            ),
        ],
    )
    resolver = router.to_urlpatterns()

    with translation.override('en'):
        assert resolver.resolve('api/books/1/').kwargs == {'pk': 1}
        assert resolver.resolve('api/shop/shelf/').url_name == 'shelf'
        with pytest.raises(Resolver404):
            resolver.resolve('api/knigi/1/')

    with translation.override('ru'):
        assert resolver.resolve('api/knigi/1/').kwargs == {'pk': 1}
        assert resolver.resolve('api/magazin/shelf/').url_name == 'shelf'
        with pytest.raises(Resolver404):
            resolver.resolve('api/books/1/')
