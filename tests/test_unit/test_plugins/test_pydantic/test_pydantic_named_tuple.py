import json
import uuid
from http import HTTPStatus
from typing import NamedTuple, final

from dirty_equals import IsStr, IsUUID
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _BodyModel(NamedTuple):
    uid: uuid.UUID
    email: str


@final
class _FieldsController(
    Controller[PydanticSerializer],
):
    def post(self, parsed_body: Body[_BodyModel]) -> _BodyModel:
        return parsed_body


def test_named_tuple_pydantic_serialization(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that named tuple pydantic serialization works well."""
    request_data = {
        'uid': uuid.uuid4(),
        'email': faker.email(),
    }

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _FieldsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == snapshot([IsUUID, IsStr()])


def test_named_tuple_arbitrary_types(dmr_rf: DMRRequestFactory) -> None:
    """Ensures by arbitrary types in named tuple produce clear errors."""
    request_data = {
        'uid': 1,
        'email': 2,
    }

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _FieldsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'UUID input should be a string, bytes or UUID object',
                'loc': ['parsed_body', 'uid'],
                'type': 'value_error',
            },
            {
                'msg': 'Input should be a valid string',
                'loc': ['parsed_body', 'email'],
                'type': 'value_error',
            },
        ],
    })
