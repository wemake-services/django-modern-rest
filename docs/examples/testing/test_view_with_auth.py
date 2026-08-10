import json
from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr.security.token.app.models import Token
from dmr.test import DMRRequestFactory
from examples.auth.token.using_token_header import APIController


@pytest.fixture
def token_auth(admin_user: User) -> tuple[Token, str]:
    return Token.issue(user=admin_user, name='test-token')


def test_view_with_auth(
    dmr_rf: DMRRequestFactory,
    token_auth: tuple[Token, str],
) -> None:
    request = dmr_rf.get('/api/url', headers={'X-API-Token': token_auth[1]})

    response = APIController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'
