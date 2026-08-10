import pytest
from django.urls import URLResolver

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


class _UserController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


user_router = Router(
    prefix='users/',
    urls=[path('user/', _UserController.as_view())],
)


def test_router_include() -> None:
    """Ensure that router.include() works as expected."""
    router = Router(prefix='api/v1/')
    router.include(user_router)

    assert len(router.urls) == 1
    assert isinstance(router.urls[0], URLResolver)
    assert user_router.urls == router.urls[0].urlconf_module


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
    """Ensure that router.include() works as expected with arguments."""
    router = Router(prefix='api/v1/')
    router.include(user_router, app_name, namespace=namespace)

    assert len(router.urls) == 1
    assert isinstance(router.urls[0], URLResolver)
    assert router.urls[0].namespace == expected_namespace
    assert router.urls[0].app_name == expected_app_name
