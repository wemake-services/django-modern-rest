from http import HTTPStatus

from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient


def test_user_update_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that async ``put`` routes work."""
    user_id = faker.random_int()
    response = dmr_client.put(
        reverse('api:controllers:user_update', kwargs={'user_id': user_id}),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': 'new@email.com', 'age': user_id}


def test_user_replace_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that async ``patch`` routes work."""
    user_id = faker.unique.random_int()
    email = faker.email()
    response = dmr_client.patch(
        reverse('api:controllers:user_update', kwargs={'user_id': user_id}),
        data={'email': email, 'age': faker.unique.random_int(min=1)},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': email, 'age': user_id}


def test_user_replace_view404(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that async ``patch`` produces ``404``."""
    response = dmr_client.patch(
        reverse('api:controllers:user_update', kwargs={'user_id': 0}),
        data={'email': faker.email(), 'age': faker.unique.random_int(min=1)},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [
            {
                'msg': 'Object does not exist',
                'loc': ['parsed_path', 'user_id'],
                'type': 'not_found',
            },
        ],
    })
