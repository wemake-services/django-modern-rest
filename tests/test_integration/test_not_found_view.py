from http import HTTPMethod, HTTPStatus

import pytest
from django.conf import LazySettings
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.mark.parametrize('method', list(HTTPMethod))
def test_not_found_view(
    dmr_client: DMRClient,
    settings: LazySettings,
    *,
    method: HTTPMethod,
) -> None:
    """Test that 404 view works."""
    if settings.DEBUG:
        pytest.skip(reason='404 does not work with DEBUG=True')

    response = dmr_client.generic(str(method), '/api/missing')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers['Content-Type'] == 'application/json'
    if method == HTTPMethod.HEAD:
        assert not response.content
    else:
        assert response.json() == snapshot({
            'detail': [{'msg': 'Page not found', 'type': 'not_found'}],
        })
