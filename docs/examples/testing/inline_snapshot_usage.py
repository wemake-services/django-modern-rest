import json
from http import HTTPStatus

from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr.test import DMRRequestFactory
from examples.testing.pydantic_controller import UserController


def test_complete_validation_error(dmr_rf: DMRRequestFactory) -> None:
    request = dmr_rf.post('/users/', data={})

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'email'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'age'],
                'type': 'value_error',
            },
        ],
    })
