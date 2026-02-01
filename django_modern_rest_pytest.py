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
    from django_modern_rest.test import (
        DMRAsyncClient,
        DMRAsyncRequestFactory,
        DMRClient,
        DMRRequestFactory,
    )


@pytest.fixture
def dmr_client() -> 'DMRClient':
    """Customized version of :class:`django.test.Client`."""
    from django_modern_rest.test import DMRClient

    return DMRClient()


@pytest.fixture
def dmr_async_client() -> 'DMRAsyncClient':
    """Customized version of :class:`django.test.AsyncClient`."""
    from django_modern_rest.test import DMRAsyncClient

    return DMRAsyncClient()


@pytest.fixture
def dmr_rf() -> 'DMRRequestFactory':
    """Customized version of :class:`django.test.RequestFactory`."""
    from django_modern_rest.test import DMRRequestFactory

    return DMRRequestFactory()


@pytest.fixture
def dmr_async_rf() -> 'DMRAsyncRequestFactory':
    """Customized version of :class:`django.test.AsyncRequestFactory`."""
    from django_modern_rest.test import DMRAsyncRequestFactory

    return DMRAsyncRequestFactory()


@pytest.fixture
def dmr_clean_settings() -> Iterator[None]:
    """Cleans settings caches before and after the test."""
    from django_modern_rest.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()
