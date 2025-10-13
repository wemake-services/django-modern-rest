from http import HTTPStatus

from django.urls import reverse

from django_modern_rest.test import DMRClient


# TODO: use `faker` for all test data
def test_user_update_view(dmr_client: DMRClient) -> None:
    """Ensure that async `put` routes work."""
    response = dmr_client.put(
        reverse('api:user_update', kwargs={'user_id': 1}),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': 'new@email.com', 'age': 1}


def test_user_replace_view(dmr_client: DMRClient) -> None:
    """Ensure that async `patch` routes work."""
    response = dmr_client.patch(
        reverse('api:user_update', kwargs={'user_id': 1}),
        data={'email': 'test@example.com', 'age': 3},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'email': 'test@example.com', 'age': 1}


def test_wrong_method(dmr_client: DMRClient) -> None:
    """Ensure 405 is correctly handled."""
    response = dmr_client.post(
        reverse('api:user_update', kwargs={'user_id': 1}),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: assert content-type and error handling
