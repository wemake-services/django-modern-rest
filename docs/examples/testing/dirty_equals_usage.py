import json
from http import HTTPStatus

from dirty_equals import IsUUID
from django.http import HttpResponse

from dmr.test import DMRRequestFactory
from examples.testing.pydantic_controller import UserController


def test_dynamic_user_identifier(dmr_rf: DMRRequestFactory) -> None:
    request_data = {'email': 'test@example.com', 'age': 43}
    request = dmr_rf.post('/users/', data=request_data)

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == {
        'uid': IsUUID(4),
        **request_data,
    }
