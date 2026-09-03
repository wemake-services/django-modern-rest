import json
from http import HTTPStatus

from dirty_equals import IsUUID
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr.test import DMRRequestFactory
from examples.testing.pydantic_controller import UserController


def test_complete_user_response(dmr_rf: DMRRequestFactory) -> None:
    request = dmr_rf.post(
        '/users/',
        data={'email': 'test@example.com', 'age': 43},
    )

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == snapshot({
        'uid': IsUUID(),
        'email': 'test@example.com',
        'age': 43,
    })
