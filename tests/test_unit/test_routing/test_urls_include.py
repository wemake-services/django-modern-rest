import json

import pytest
from django.urls import URLResolver, include
from django.urls import path as django_path
from django.utils import translation
from django.utils.functional import lazy
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.internal.types import StrOrPromise
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path


def _lazy_route(english: str, russian: str) -> StrOrPromise:
    def translate() -> str:
        if translation.get_language() == 'ru':
            return russian
        return english

    return lazy(translate, str)()


class _UserController(Controller[PydanticFastSerializer]):
    def get(self) -> str:
        raise NotImplementedError


_user_router = Router(
    prefix='users/',
    urls=[path('user/', _UserController.as_view())],
)


class _OtherController(Controller[PydanticFastSerializer]):
    def get(self) -> str:
        raise NotImplementedError


def test_router_include() -> None:
    """Ensure that `router.include()` works as expected."""
    router = Router(
        prefix='api/v1/',
        urls=[path('other/', _OtherController.as_view())],
    )
    router.include(_user_router)

    assert len(router.urls) == 2
    assert len(_user_router.urls) == 1


@pytest.mark.parametrize(
    ('app_name', 'namespace', 'expected_app_name', 'expected_namespace'),
    [
        (None, None, None, None),
        ('urls', None, 'urls', 'urls'),
        (None, 'urls', 'urls', 'urls'),
        ('urls_app_name', 'urls_namespace', 'urls_app_name', 'urls_namespace'),
    ],
)
def test_router_include_with_args(
    *,
    app_name: str | None,
    namespace: str | None,
    expected_app_name: str | None,
    expected_namespace: str | None,
) -> None:
    """Ensure that `router.include()` works as expected with arguments."""
    router = Router(prefix='api/v1/')
    router.include(_user_router, namespace=namespace, app_name=app_name)

    assert len(router.urls) == 1
    assert isinstance(router.urls[0], URLResolver)
    assert router.urls[0].namespace == expected_namespace
    assert router.urls[0].app_name == expected_app_name


def test_router_to_urlpatterns() -> None:
    """Ensure that `router.to_urlpatterns()` works as expected."""
    router = Router(
        prefix='api/v1/',
        urls=[path('other/', _OtherController.as_view())],
    )

    patterns = router.to_urlpatterns()

    assert isinstance(patterns, URLResolver)
    assert patterns.default_kwargs == {}
    assert patterns.namespace is None
    assert patterns.app_name is None


def test_router_to_urlpatterns_all_args() -> None:
    """Ensure that `router.to_urlpatterns()` works as expected."""
    router = Router(
        prefix='api/v1/',
        urls=[path('other/', _OtherController.as_view())],
    )

    patterns = router.to_urlpatterns(namespace='/x', app_name='y')

    assert isinstance(patterns, URLResolver)
    assert patterns.default_kwargs == {}
    assert patterns.namespace == '/x'
    assert patterns.app_name == 'y'


def test_router_include_with_metadata(
    snapshot: SnapshotAssertion,
) -> None:
    """Ensure that `router.include()` metadata works as expected."""
    level1 = Router(
        prefix='old/',
        urls=[path('user/', _UserController.as_view())],
        tags=['level1'],
        deprecated=True,
    )

    level2 = Router(
        prefix='users/',
        urls=[path('user/', _UserController.as_view())],
    )
    level2.include(level1)

    router = Router(
        prefix='api/',
        urls=[path('other/', _OtherController.as_view())],
        tags=['level3'],
    )
    router.include(level2)

    assert (
        json.dumps(
            build_schema(router).convert(),
            indent=2,
        )
        == snapshot
    )


def test_nested_router_ignore_from_spec() -> None:
    """Ensure that `ignore_from_spec` propagates through nested routers."""
    hidden_router = Router(
        prefix='private/',
        urls=[path('user/', _UserController.as_view())],
        ignore_from_spec=True,
    )
    version_router = Router(
        prefix='v1/',
        urls=[path('other/', _OtherController.as_view())],
    )
    version_router.include(hidden_router)
    router = Router(prefix='api/')
    router.include(version_router)

    schema = build_schema(router)

    assert schema.paths is not None
    assert set(schema.paths) == {'/api/v1/other/'}


@pytest.mark.parametrize(
    ('prefix', 'expected_path'),
    [
        ('users', '/api/users'),
        ('/users', '/api/users'),
        ('users/', '/api/users/'),
    ],
)
def test_router_include_empty_pattern(
    prefix: str,
    expected_path: str,
) -> None:
    """Ensure that `router.include()` works with empty patterns, #1657."""
    users = Router(
        prefix=prefix,
        urls=[path('', _UserController.as_view(), name='users')],
        tags=['users'],
    )
    router = Router(prefix='api', tags=['api'])
    router.include(users, namespace='users')

    schema = build_schema(router).convert()

    assert set(schema['paths']) == {expected_path}
    assert schema['paths'][expected_path]['get']['tags'] == ['api', 'users']


def test_router_nested_empty_patterns() -> None:
    """Ensure that nested empty patterns work in schema generation, #1657."""
    inner = Router(
        prefix='inner/',
        urls=[path('', _UserController.as_view())],
        ignore_from_spec=True,
    )
    users = Router(
        prefix='users/',
        urls=[
            path('', include([path('', _OtherController.as_view())])),
        ],
    )
    users.include(inner)
    router = Router(prefix='')
    router.include(users)

    schema = build_schema(router)

    assert schema.paths is not None
    assert set(schema.paths) == {'/users/'}
    assert router.metadata_for('/users/inner/').ignore_from_spec is True


def test_translated_route_build_schema() -> None:
    """Ensure ``build_schema()`` works across active languages, #1700."""
    router = Router(
        'api/',
        [
            path(
                _lazy_route('books/<int:pk>/', 'knigi/<int:pk>/'),
                _UserController.as_view(),
            ),
        ],
        tags=['library'],
    )

    with translation.override('en'):
        en_schema = build_schema(router).convert()
        assert set(en_schema['paths']) == {'/api/books/{pk}/'}
        assert en_schema['paths']['/api/books/{pk}/']['get']['tags'] == [
            'library',
        ]
        assert router.metadata_for('/api/books/{pk}/').tags == ['library']
        with pytest.raises(KeyError, match=r'/api/knigi/\{pk\}/'):
            router.metadata_for('/api/knigi/{pk}/')

    with translation.override('ru'):
        ru_schema = build_schema(router).convert()
        assert set(ru_schema['paths']) == {'/api/knigi/{pk}/'}
        assert ru_schema['paths']['/api/knigi/{pk}/']['get']['tags'] == [
            'library',
        ]
        assert router.metadata_for('/api/knigi/{pk}/').tags == ['library']
        with pytest.raises(KeyError, match=r'/api/books/\{pk\}/'):
            router.metadata_for('/api/books/{pk}/')


def test_translated_route_included_routers() -> None:
    """Ensure ``Router.include()`` preserves metadata across languages."""
    books = Router(
        '',
        [
            path(
                _lazy_route('books/<int:pk>/', 'knigi/<int:pk>/'),
                _UserController.as_view(),
            ),
            django_path(
                _lazy_route('shop/', 'magazin/'),
                include([
                    django_path(
                        _lazy_route('nested/', 'vlozh/'),
                        _OtherController.as_view(),
                    ),
                ]),
            ),
        ],
        tags=['books'],
        deprecated=True,
    )
    hidden = Router(
        '',
        [
            django_path(
                _lazy_route('secret/', 'sekret/'),
                _OtherController.as_view(),
            ),
        ],
        ignore_from_spec=True,
    )
    router = Router('api/', tags=['api'])
    router.include(books)
    router.include(hidden)

    with translation.override('en'):
        en_schema = build_schema(router).convert()
        assert set(en_schema['paths']) == {
            '/api/books/{pk}/',
            '/api/shop/nested/',
        }
        assert en_schema['paths']['/api/books/{pk}/']['get']['tags'] == [
            'api',
            'books',
        ]
        assert (
            en_schema['paths']['/api/books/{pk}/']['get']['deprecated'] is True
        )
        assert router.metadata_for('/api/secret/').ignore_from_spec is True

    with translation.override('ru'):
        ru_schema = build_schema(router).convert()
        assert set(ru_schema['paths']) == {
            '/api/knigi/{pk}/',
            '/api/magazin/vlozh/',
        }
        assert ru_schema['paths']['/api/knigi/{pk}/']['get']['tags'] == [
            'api',
            'books',
        ]
        assert (
            ru_schema['paths']['/api/knigi/{pk}/']['get']['deprecated'] is True
        )
        assert router.metadata_for('/api/sekret/').ignore_from_spec is True


def test_reused_subrouter_metadata() -> None:
    """Ensure the same sub-router included twice keeps distinct metadata."""
    shared = Router(
        'items/',
        [path('', _UserController.as_view())],
        tags=['shared'],
    )
    v1 = Router('v1/', tags=['v1'], deprecated=True)
    v1.include(shared)
    v2 = Router('v2/', tags=['v2'], deprecated=False)
    v2.include(shared)

    api = Router('api/')
    api.include(v1)
    api.include(v2)

    schema = build_schema(api).convert()

    assert schema['paths']['/api/v1/items/']['get']['tags'] == ['v1', 'shared']
    assert schema['paths']['/api/v1/items/']['get']['deprecated'] is True
    assert schema['paths']['/api/v2/items/']['get']['tags'] == ['v2', 'shared']
    assert 'deprecated' not in schema['paths']['/api/v2/items/']['get']
