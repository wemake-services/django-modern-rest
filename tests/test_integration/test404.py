from http import HTTPMethod, HTTPStatus

import pytest
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.mark.parametrize('method', set(HTTPMethod))
def test404_view(
    dmr_client: DMRClient,
    *,
    method: HTTPMethod,
) -> None:
    """Test that 404 view works."""
    response = dmr_client.generic(str(method), '/api/missing')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers['Content-Type'] == 'application/json'
    if method == HTTPMethod.HEAD:
        assert not response.content
    else:
        assert response.json() == snapshot({
            'detail': [{'msg': 'Page not found', 'type': 'not_found'}],
        })
