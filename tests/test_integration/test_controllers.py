import pytest
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
    base_url = reverse('api:user_create')
    start_from_query = '' if start_from is None else f'&start_from={start_from}'

    response = client.post(
        f'{base_url}?q=text{start_from_query}',
        headers={'X-API-Token': 'token'},
        json={'email': 'whatever@email.com', 'age': 0},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert 'Content-Type' in response.headers


def test_user_update_controller(client: Client) -> None:
    """Test UserUpdateController with PATCH request."""
    url = reverse('api:user_update', kwargs={'user_id': 123})

    response = client.patch(
        url,
        json={'email': 'updated@email.com', 'age': 25},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert 'Content-Type' in response.headers
