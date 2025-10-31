import sys

import pytest

if sys.version_info >= (3, 14):
    pytest.skip(reason='Module does not supported yet', allow_module_level=True)

import json  # type: ignore[unreachable, unused-ignore]
from http import HTTPStatus
from typing import final

from dirty_equals import IsUUID
from django.http import HttpResponse
from polyfactory.factories.pydantic_factory import ModelFactory

from django_modern_rest.test import DMRRequestFactory
from examples.testing.pydantic_controller import UserController, UserCreateModel


@final
class UserCreateModelFactory(ModelFactory[UserCreateModel]):
    """Will create structured random request data for you."""

    __check_model__ = True


def test_create_user(dmr_rf: DMRRequestFactory) -> None:
    # This will return random `UserCreatedModel` instances:
    request_data = UserCreateModelFactory.build().model_dump(mode='json')

    request = dmr_rf.post('/url/', data=request_data)

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'uid': IsUUID,
        **request_data,
    }
