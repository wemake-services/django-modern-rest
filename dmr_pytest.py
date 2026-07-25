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
    from collections.abc import Awaitable, Callable
    from contextlib import AbstractContextManager

    from django.conf import LazySettings
    from django.http import HttpResponse

    from dmr.test import (
        DMRAsyncClient,
        DMRAsyncRequestFactory,
        DMRClient,
        DMRRequestFactory,
    )
    from dmr.throttling import AsyncThrottle, SyncThrottle


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
def dmr_reduced_throttling() -> (
    'Callable[..., AbstractContextManager[SyncThrottle | AsyncThrottle]]'
):
    """Provides :func:`dmr.test.reduced_throttling`."""
    from dmr.test import reduced_throttling

    return reduced_throttling


@pytest.fixture
def dmr_assert_throttled() -> 'Callable[..., None]':
    """Provides :func:`dmr.test.assert_throttled`."""
    from dmr.test import assert_throttled

    return assert_throttled


@pytest.fixture
def dmr_assert_throttling() -> 'Callable[..., HttpResponse]':
    """Provides :func:`dmr.test.assert_throttling`."""
    from dmr.test import assert_throttling

    return assert_throttling


@pytest.fixture
def dmr_assert_async_throttling() -> 'Callable[..., Awaitable[HttpResponse]]':
    """Provides :func:`dmr.test.assert_async_throttling`."""
    from dmr.test import assert_async_throttling

    return assert_async_throttling


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
