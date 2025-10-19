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
    from django_modern_rest.test import DMRClient  # noqa: PLC0415

    return DMRClient()


@pytest.fixture
def dmr_async_client() -> 'DMRAsyncClient':
    """Customized version of :class:`django.test.AsyncClient`."""
    from django_modern_rest.test import DMRAsyncClient  # noqa: PLC0415

    return DMRAsyncClient()


@pytest.fixture
def dmr_client_csrf() -> 'DMRClient':
    """Customized version of :class:`django.test.Client` with csrf."""
    from django_modern_rest.test import DMRClient  # noqa: PLC0415

    return DMRClient(enforce_csrf_checks=True)


@pytest.fixture
def dmr_async_client_csrf() -> 'DMRAsyncClient':
    """Customized version of :class:`django.test.AsyncClient` with csrf."""
    from django_modern_rest.test import DMRAsyncClient  # noqa: PLC0415

    return DMRAsyncClient(enforce_csrf_checks=True)


@pytest.fixture
def dmr_rf() -> 'DMRRequestFactory':
    """Customized version of :class:`django.test.RequestFactory`."""
    from django_modern_rest.test import DMRRequestFactory  # noqa: PLC0415

    return DMRRequestFactory()


@pytest.fixture
def dmr_async_rf() -> 'DMRAsyncRequestFactory':
    """Customized version of :class:`django.test.AsyncRequestFactory`."""
    from django_modern_rest.test import DMRAsyncRequestFactory  # noqa: PLC0415

    return DMRAsyncRequestFactory()
