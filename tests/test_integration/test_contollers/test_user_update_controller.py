from http import HTTPStatus

from django.urls import reverse
from faker import Faker

from django_modern_rest.test import DMRClient


def test_user_update_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that async `put` routes work."""
    user_id = faker.random_int()
    response = dmr_client.put(
        reverse('api:user_update', kwargs={'user_id': user_id}),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': 'new@email.com', 'age': user_id}


def test_user_replace_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure that async `patch` routes work."""
    user_id = faker.unique.random_int()
    email = faker.email()
    response = dmr_client.patch(
        reverse('api:user_update', kwargs={'user_id': user_id}),
        data={'email': email, 'age': faker.unique.random_int()},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': email, 'age': user_id}


def test_wrong_method(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure 405 is correctly handled."""
    response = dmr_client.post(
        reverse('api:user_update', kwargs={'user_id': faker.random_int()}),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: assert content-type and error handling
