from http import HTTPMethod, HTTPStatus

import pytest
from django.conf import LazySettings
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.fixture(autouse=True)
def _modify_integration_settings(settings: LazySettings) -> None:
    # 404 view does not work with `DEBUG=True`, this test used to be skipped
    # in this mode, so there is no value in running it twice
    # via the parent conftest parametrisation.
    settings.DEBUG = False


@pytest.mark.parametrize('method', list(HTTPMethod))
def test_not_found_view(
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
