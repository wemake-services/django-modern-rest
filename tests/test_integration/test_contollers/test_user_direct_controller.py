from http import HTTPStatus
from typing import final

import pytest
from django.test import SimpleTestCase
from django.urls import reverse
from typing_extensions import override

from django_modern_rest.test import DMRAsyncClient, DMRClient


def test_user_update_direct_view(dmr_client: DMRClient) -> None:
    """Ensure that direct routes work."""
    response = dmr_client.patch(
        reverse('api:user_update_direct', kwargs={'user_id': 5}),
        data={'email': 'test@example.com', 'age': 3},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': 'test@example.com',
        'age': 5,
    }


@pytest.mark.asyncio
async def test_user_update_direct_view_async_client(
    dmr_async_client: DMRAsyncClient,
) -> None:
    """Ensure that direct routes work."""
    response = await dmr_async_client.patch(
        reverse('api:user_update_direct', kwargs={'user_id': 5}),
        data={'email': 'test@example.com', 'age': 3},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': 'test@example.com',
        'age': 5,
    }


@final
class ClientWorksWithRegularTest(SimpleTestCase):
    """Ensure that regular django-style unittests also work."""

    @override
    def setUp(self) -> None:
        self._dmr_client = DMRClient()
        self._dmr_async_client = DMRAsyncClient()

    def test_user_update_direct_view(self) -> None:
        """Sync test."""
        response = self._dmr_client.patch(
            reverse('api:user_update_direct', kwargs={'user_id': 5}),
            data={'email': 'test@example.com', 'age': 3},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.headers['Content-Type'] == 'application/json'

    async def test_user_update_direct_view_async(self) -> None:
        """Async test."""
        response = await self._dmr_async_client.patch(
            reverse('api:user_update_direct', kwargs={'user_id': 5}),
            data={'email': 'test@example.com', 'age': 3},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.headers['Content-Type'] == 'application/json'


def test_user_update_direct_view405(dmr_client: DMRClient) -> None:
    """Ensure that direct routes raise 405."""
    response = dmr_client.delete(
        reverse('api:user_update_direct', kwargs={'user_id': 5}),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: test error reporting
