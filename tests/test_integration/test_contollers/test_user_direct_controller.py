from http import HTTPStatus
from typing import final

import pytest
from django.test import SimpleTestCase
from django.urls import reverse
from faker import Faker
from typing_extensions import override

from django_modern_rest.test import DMRAsyncClient, DMRClient


def test_user_update_direct_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that direct routes work."""
    email = faker.email()
    user_id = faker.unique.random_int()

    response = dmr_client.patch(
        reverse('api:user_update_direct', kwargs={'user_id': user_id}),
        data={'email': email, 'age': faker.unique.random_int()},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': email,
        'age': user_id,
    }


@pytest.mark.asyncio
async def test_user_update_direct_view_async_client(
    dmr_async_client: DMRAsyncClient,
    faker: Faker,
) -> None:
    """Ensure that direct routes work."""
    email = faker.email()
    user_id = faker.unique.random_int()

    response = await dmr_async_client.patch(
        reverse('api:user_update_direct', kwargs={'user_id': user_id}),
        data={'email': email, 'age': faker.unique.random_int()},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': email,
        'age': user_id,
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
        # We don't use `faker` here, because it is hard to inject
        # a reproduceable seeds into a native unittest test.
        # And this needs to be a pure unittest test.
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
