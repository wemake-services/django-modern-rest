from http import HTTPStatus

import pytest
from django.conf import LazySettings
from django.urls import reverse
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.mark.parametrize(
    ('language_code', 'expected_message'),
    [
        ('ru', 'Не аутентифицирован'),  # noqa: RUF001
        ('ko', '인증되지 않았습니다.'),
        ('ko-KR', '인증되지 않았습니다.'),
    ],
)
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
def test_missing_auth_with_accept_language(
    dmr_client: DMRClient,
    reset_language: None,
    settings: LazySettings,
    *,
    url: str,
    language_code: str,
    expected_message: str,
) -> None:
    """Ensure auth errors respect language preferences without leaking state."""
    settings.LANGUAGES = (*settings.LANGUAGES, ('ko', 'Korean'))
    response = dmr_client.post(
        url,
        data='{}',
        headers={'Accept-Language': language_code},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'detail': [
            {
                'msg': expected_message,
                'type': 'security',
            },
        ],
    }

    # Second request in the same context, it is important:
    response = dmr_client.post(
        url,
        data='{}',
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })

    # Default in the same context, it is important:
    response = dmr_client.post(
        url,
        data='{}',
        headers={'Accept-Language': 'en'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })

    # Last request in the same context, order is very important,
    # last test must not set the default `en` locale:
    response = dmr_client.post(
        url,
        data='{}',
        headers={'Accept-Language': 'kk'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Аутентификация жасалмаған', 'type': 'security'}],
    })
