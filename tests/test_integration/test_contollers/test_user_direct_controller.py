from http import HTTPStatus

from django.test import Client
from django.urls import reverse


def test_user_update_direct_view(client: Client) -> None:
    """Ensure that direct routes work."""
    response = client.patch(
        reverse('api:user_update_direct', kwargs={'user_id': 5}),
        content_type='application/json',
        data={'email': 'test@example.com', 'age': 3},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'email': 'test@example.com',
        'age': 5,
    }


def test_user_update_direct_view405(client: Client) -> None:
    """Ensure that direct routes raise 405."""
    response = client.delete(
        reverse('api:user_update_direct', kwargs={'user_id': 5}),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: test error reporting
