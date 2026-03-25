from http import HTTPStatus

from django.urls import reverse
from inline_snapshot import snapshot

from dmr.test import DMRClient


def test_conditional_etag_controller_not_modified(
    dmr_client: DMRClient,
) -> None:
    """Ensure conditional ETag has explicit content type for 304."""
    user_id = 1
    endpoint = reverse('api:etag:user', kwargs={'user_id': user_id})
    response = dmr_client.get(endpoint)

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/json'
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
    assert conditional.headers['Content-Type'] == 'application/json'
