from http import HTTPStatus

import pytest
from django.urls import reverse
from faker import Faker

from dmr.test import DMRAsyncClient, DMRClient


def test_user_update_direct_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that direct routes work."""
    email = faker.email()
    user_id = faker.unique.random_int()

    response = dmr_client.patch(
        reverse(
            'api:controllers:user_update_direct',
            kwargs={'user_id': user_id},
        ),
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
        reverse(
            'api:controllers:user_update_direct',
            kwargs={'user_id': user_id},
        ),
        data={'email': email, 'age': faker.unique.random_int()},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': email,
        'age': user_id,
    }


def test_user_update_direct_re(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that re_path with named groups is allowed."""
    email = faker.email()
    user_id = faker.unique.random_int(min=1)

    response = dmr_client.patch(
        reverse('api:controllers:user_update_direct_re', args=(user_id,)),
        data={'email': email, 'age': faker.unique.random_int(min=1)},
    )

    assert response.status_code == HTTPStatus.OK, response.json()
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': email,
        'age': user_id,
    }
