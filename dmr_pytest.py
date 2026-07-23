from collections.abc import Iterator
from typing import TYPE_CHECKING

try:
    import pytest
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pytest` is not installed, please install it separately',
    )
    raise

if TYPE_CHECKING:
    # We can't import it directly, because it will ruin our coverage measures.
    from collections.abc import Callable

    from django.conf import LazySettings

    from dmr.test import (
        DMRAsyncClient,
        DMRAsyncRequestFactory,
        DMRClient,
        DMRRequestFactory,
        _ThrottleState,  # noqa: WPS450
    )


@pytest.fixture
def dmr_client(request: pytest.FixtureRequest) -> 'DMRClient':
    """Customized version of :class:`django.test.Client`."""
    from dmr.internal.test import maybe_track_client
    from dmr.test import DMRClient

    client = DMRClient()
    maybe_track_client(request, client)
    return client


@pytest.fixture
def dmr_async_client(request: pytest.FixtureRequest) -> 'DMRAsyncClient':
    """Customized version of :class:`django.test.AsyncClient`."""
    from dmr.internal.test import maybe_track_client
    from dmr.test import DMRAsyncClient

    client = DMRAsyncClient()
    maybe_track_client(request, client)
    return client


@pytest.fixture
def dmr_rf() -> 'DMRRequestFactory':
    """Customized version of :class:`django.test.RequestFactory`."""
    from dmr.test import DMRRequestFactory

    return DMRRequestFactory()


@pytest.fixture
def dmr_async_rf() -> 'DMRAsyncRequestFactory':
    """Customized version of :class:`django.test.AsyncRequestFactory`."""
    from dmr.test import DMRAsyncRequestFactory

    return DMRAsyncRequestFactory()


@pytest.fixture
def dmr_throttle_state() -> 'Callable[..., _ThrottleState]':
    """
    Factory to exhaust a controller's throttles in tests.

    Returns :func:`dmr.test.throttle_state`::

        def test_throttled(dmr_rf, dmr_throttle_state):
            dmr_throttle_state(MyController).exhaust(dmr_rf.get('/whatever/'))
            response = MyController.as_view()(dmr_rf.get('/whatever/'))
            assert_throttled(response)
    """
    from dmr.test import throttle_state

    return throttle_state


@pytest.fixture
def dmr_clean_settings() -> Iterator[None]:
    """Cleans settings caches before and after the test."""
    from dmr.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def settings(
    settings: 'LazySettings',
    dmr_clean_settings: None,
) -> 'LazySettings':
    """Customized version of :func:`pytest_django.fixtures.settings`."""
    return settings
