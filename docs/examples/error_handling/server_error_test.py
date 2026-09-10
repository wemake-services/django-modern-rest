from http import HTTPStatus

from django.http import HttpResponse

from dmr.test import DMRRequestFactory
from examples.error_handling.server_error_undocumented import UserController


def test_no_server_errors() -> None:
    """Ensures that regular requests never return a `500`."""
    request = DMRRequestFactory().post(
        '/api/user/',
        data={'email': 'user@wms.org'},
        content_type='application/json',
    )

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
