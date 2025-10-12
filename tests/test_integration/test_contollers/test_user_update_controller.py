from http import HTTPStatus

from django.test import Client
from django.urls import reverse


# TODO: use `faker` for all test data
def test_user_update_view(client: Client) -> None:
    """Ensure that async `put` routes work."""
    response = client.put(
        reverse('api:user_update', kwargs={'user_id': 1}),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': 'new@email.com', 'age': 1}


def test_user_replace_view(client: Client) -> None:
    """Ensure that async `patch` routes work."""
    response = client.patch(
        reverse('api:user_update', kwargs={'user_id': 1}),
        content_type='application/json',
        data={'email': 'test@example.com', 'age': 3},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': 'test@example.com', 'age': 1}


def test_wrong_method(client: Client) -> None:
    """Ensure 405 is correctly handled."""
    response = client.post(reverse('api:user_update', kwargs={'user_id': 1}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: assert content-type and error handling
