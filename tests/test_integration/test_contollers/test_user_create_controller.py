from http import HTTPStatus

import pytest
from dirty_equals import IsUUID
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

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
    base_url = reverse('api:controllers:users')
    start_from_query = '' if start_from is None else f'&start_from={start_from}'
    request_data = {'email': faker.email(), 'age': faker.random_int()}
    response = dmr_client.post(
        f'{base_url}?q=text{start_from_query}',
        headers={'X-API-Token': 'token'},
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        **request_data,
        'query': 'text',
        'start_from': start_from,
        'token': 'token',
        'uid': IsUUID,
    }


def test_user_create_view_multiple_errors(
    dmr_client: DMRClient,
) -> None:
    """Ensure that all errors are shown at once."""
    response = dmr_client.post(
        reverse('api:controllers:users'),
        headers={},
        data={},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_query', 'q'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_headers', 'X-API-Token'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'email'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'age'],
                'type': 'value_error',
            },
        ],
    })


def test_user_list_view(dmr_client: DMRClient) -> None:
    """Ensure that list routes work."""
    response = dmr_client.get(reverse('api:controllers:users'))

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == [
        {'email': 'first@example.org', 'age': 1},
        {'email': 'second@example.org', 'age': 2},
    ]


def test_constrained_user_view(dmr_client: DMRClient, faker: Faker) -> None:
    """Ensure constrained endpoint works correctly."""
    request_data = {
        'username': faker.user_name(),
        'age': faker.random_int(min=18, max=100),  # noqa: WPS432
        'score': faker.pyfloat(min_value=0, max_value=1.5),  # noqa: WPS432
    }
    response = dmr_client.post(
        reverse('api:controllers:constrained_user_create'),
        data=request_data,
    )
    assert response.status_code == HTTPStatus.CREATED
