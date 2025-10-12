from http import HTTPStatus

import pytest
from dirty_equals import IsUUID
from django.test import Client
from django.urls import reverse


@pytest.mark.parametrize(
    'start_from',
    [
        '2025-10-09T20:19:55',
        None,
    ],
)
def test_user_create_view(client: Client, *, start_from: str | None) -> None:
    """Ensure that routes without path parameters work."""
    base_url = reverse('api:users')
    start_from_query = '' if start_from is None else f'&start_from={start_from}'
    response = client.post(
        f'{base_url}?q=text{start_from_query}',
        headers={'X-API-Token': 'token'},
        data={'email': 'whatever@email.com', 'age': 0},
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'age': 0,
        'email': 'whatever@email.com',
        'query': 'text',
        'start_from': start_from,
        'token': 'token',
        'uid': IsUUID,
    }


# TODO: use custom `TestClient`
def test_user_list_view(client: Client) -> None:
    """Ensure that list routes work."""
    response = client.get(
        reverse('api:users'),
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == [
        {'email': 'first@mail.ru', 'age': 1},
        {'email': 'second@mail.ru', 'age': 2},
    ]


def test_wrong_method(client: Client) -> None:
    """Ensure 405 is correctly handled."""
    response = client.put(reverse('api:users'))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: assert content-type and error handling
