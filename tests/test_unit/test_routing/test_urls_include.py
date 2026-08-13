import pytest
from django.urls import URLResolver

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path


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
