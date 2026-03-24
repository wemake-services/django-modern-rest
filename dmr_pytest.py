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
    from dmr.test import (
        DMRAsyncClient,
        DMRAsyncRequestFactory,
        DMRClient,
        DMRRequestFactory,
    )


def _maybe_track_client(
    request: pytest.FixtureRequest,
    client: 'DMRClient | DMRAsyncClient',
) -> None:
    """
    Connect a DMR test client to TraceCov tracking.

    If the ``tracecov_map`` fixture is available and initialized, this helper
    registers the client via ``tracecov_map.django.track_client(...)`` so all
    client interactions are included in the TraceCov report. If TraceCov is not
    installed/configured, it silently does nothing.
    """
    try:
        # Optional fixture: exists only when tracecov plugin is installed.
        tracecov_map = request.getfixturevalue('tracecov_map')
    except pytest.FixtureLookupError:
        return

    # TraceCov plugin loaded, but coverage map is intentionally inactive.
    if tracecov_map is None:
        return

    tracecov_map.django.track_client(client)


@pytest.fixture
def dmr_client(request: pytest.FixtureRequest) -> 'DMRClient':
    """Customized version of :class:`django.test.Client`."""
    from dmr.test import DMRClient

    client = DMRClient()
    _maybe_track_client(request, client)
    return client


@pytest.fixture
def dmr_async_client(request: pytest.FixtureRequest) -> 'DMRAsyncClient':
    """Customized version of :class:`django.test.AsyncClient`."""
    from dmr.test import DMRAsyncClient

    client = DMRAsyncClient()
    _maybe_track_client(request, client)
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
def dmr_clean_settings() -> Iterator[None]:
    """Cleans settings caches before and after the test."""
    from dmr.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()
