from http import HTTPStatus

import pytest
from django.urls import reverse
from inline_snapshot import snapshot

from dmr.security.http import basic_auth
from dmr.test import DMRClient


@pytest.mark.parametrize(
    'url',
    [
        reverse('api:controllers:parse_headers'),
        reverse('api:controllers:async_parse_headers'),
    ],
)
@pytest.mark.parametrize(
    ('username', 'password'),
    [
        ('test', 'wrong'),
        ('wrong', 'pass'),
        ('wrong', 'wrong'),
        ('', 'pass'),
        ('test', ''),
        ('', ''),
    ],
)
def test_invalid_auth(
    dmr_client: DMRClient,
    *,
    url: str,
    username: str,
    password: str,
) -> None:
    """Ensures that wrong auth params produces the right result."""
    response = dmr_client.post(
        url,
        data='{}',
        headers={
            'Content-Type': 'application/xml',
            'Authorization': basic_auth(username, password),
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.parametrize(
    'url',
    [
        reverse('api:controllers:parse_headers'),
        reverse('api:controllers:async_parse_headers'),
    ],
)
@pytest.mark.parametrize(
    'auth_header',
    [
        '',
        'several different words',
        '12345',
        'Bearer dGVzdDpwYXNz',  # correct `test:pass` encoded, but `Bearer`
        # `test@pass` encoded:
        'dGVzdEBwYXNz',
        'Basic dGVzdEBwYXNz',
    ],
)
def test_invalid_basic_auth(
    dmr_client: DMRClient,
    *,
    url: str,
    auth_header: str,
) -> None:
    """Ensures that wrong auth params produces the right result."""
    response = dmr_client.post(
        url,
        data='{}',
        headers={
            'Content-Type': 'application/xml',
            'Authorization': auth_header,
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
