from http import HTTPStatus

import pytest
from dirty_equals import IsUUID
from django.urls import reverse
from faker import Faker

from django_modern_rest.test import DMRClient


@pytest.mark.parametrize(
    'start_from',
    [
        '2025-10-09T20:19:55',
        None,
    ],
)
def test_user_create_view(
    dmr_client: DMRClient,
    faker: Faker,
    *,
    start_from: str | None,
) -> None:
    """Ensure that routes without path parameters work."""
    base_url = reverse('api:users')
    start_from_query = '' if start_from is None else f'&start_from={start_from}'
    request_data = {'email': faker.email(), 'age': faker.random_int()}
    response = dmr_client.post(
        f'{base_url}?q=text{start_from_query}',
        headers={'X-API-Token': 'token'},
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        **request_data,
        'query': 'text',
        'start_from': start_from,
        'token': 'token',
        'uid': IsUUID,
    }


# TODO: use custom `TestClient`
def test_user_list_view(dmr_client: DMRClient) -> None:
    """Ensure that list routes work."""
    response = dmr_client.get(reverse('api:users'))

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == [
        {'email': 'first@mail.ru', 'age': 1},
        {'email': 'second@mail.ru', 'age': 2},
    ]


def test_wrong_method(dmr_client: DMRClient) -> None:
    """Ensure 405 is correctly handled."""
    response = dmr_client.put(reverse('api:users'))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    # TODO: assert content-type and error handling
