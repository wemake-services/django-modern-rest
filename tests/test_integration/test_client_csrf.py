from http import HTTPStatus

import pytest
from django.urls import reverse

from django_modern_rest.test import DMRAsyncClient, DMRClient


def test_csrf_protection_default_off(dmr_client: DMRClient) -> None:
    """Tests success request when CSRF is off."""
    response = dmr_client.post(
        reverse('api:csrf_test'),
        data={'email': 'test@example.com', 'age': 25},
    )

    assert response.status_code == HTTPStatus.CREATED


def test_csrf_without_token(dmr_client_csrf: DMRClient) -> None:
    """Tests frobidden request with csrf checks."""
    response = dmr_client_csrf.post(
        reverse('api:csrf_test'),
        data={'email': 'test@example.com', 'age': 25},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_csrf_async_without_token(
    dmr_async_client_csrf: DMRAsyncClient,
) -> None:
    """Tests frobidden async request with csrf checks."""
    response = await dmr_async_client_csrf.post(
        reverse('api:csrf_test'),
        data={'email': 'test@example.com', 'age': 25},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_csrf_with_token(dmr_client_csrf: DMRClient) -> None:
    """Tests protected csrf request."""
    response = dmr_client_csrf.get(reverse('api:csrf_token'))
    assert response.status_code == HTTPStatus.OK

    csrf_token = dmr_client_csrf.cookies.get('csrftoken')
    assert csrf_token is not None

    response = dmr_client_csrf.post(
        reverse('api:csrf_test'),
        data={'email': 'test@example.com', 'age': 25},
        headers={'X-CSRFToken': csrf_token.value},
    )

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
async def test_csrf_async_with_token(
    dmr_async_client_csrf: DMRAsyncClient,
) -> None:
    """Tests protected csrf async request."""
    response = await dmr_async_client_csrf.get(reverse('api:csrf_token'))
    assert response.status_code == HTTPStatus.OK

    csrf_token = dmr_async_client_csrf.cookies.get('csrftoken')
    assert csrf_token is not None

    response = await dmr_async_client_csrf.post(
        reverse('api:csrf_test'),
        data={'email': 'test@example.com', 'age': 25},
        headers={'X-CSRFToken': csrf_token.value},
    )

    assert response.status_code == HTTPStatus.CREATED
