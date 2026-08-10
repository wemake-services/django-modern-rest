import json
from http import HTTPStatus

from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr.test import DMRRequestFactory, disabled_auth
from examples.auth.token.using_token_header import APIController, token_auth


def test_view_disabled_auth(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    request = dmr_rf.get('/api/url')

    with disabled_auth(
        APIController,
        request=request,
        user=admin_user,
        auth=token_auth,
    ):
        # No `X-API-Token` header is passed:
        response = APIController.as_view()(request)

    # But, request is successful:
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'
