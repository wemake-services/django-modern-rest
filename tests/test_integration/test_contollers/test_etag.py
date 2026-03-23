from http import HTTPStatus
from typing import Final

from django.urls import reverse
from inline_snapshot import snapshot

from dmr.test import DMRClient

_ETAG_ENDPOINT_NAME: Final = 'api:etag:user'
_APPLICATION_JSON_HEADER: Final = 'application/json'


def test_conditional_etag_controller_not_modified(
    dmr_client: DMRClient,
) -> None:
    """Ensure conditional ETag has explicit content type for 304."""
    user_id = 1
    endpoint = reverse(_ETAG_ENDPOINT_NAME, kwargs={'user_id': user_id})
    response = dmr_client.get(endpoint)

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == _APPLICATION_JSON_HEADER
    assert response.json() == snapshot({
        'message': f'Fresh content for user #{user_id}',
        'updated_at': '2026-03-23T12:30:00+00:00',
    })

    etag = response.headers['ETag']
    conditional = dmr_client.get(
        endpoint,
        headers={'If-None-Match': etag},
    )

    assert conditional.status_code == HTTPStatus.NOT_MODIFIED
    assert not conditional.content
    assert conditional.headers['ETag'] == etag
    assert conditional.headers['Content-Type'] == _APPLICATION_JSON_HEADER
