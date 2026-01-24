import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import (
    Body,
    Controller,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _RequestModel(pydantic.BaseModel):
    username: str


@final
class _UsernameController(
    Controller[PydanticSerializer],
    Body[_RequestModel],
):
    def post(self) -> str:
        return self.parsed_body.username


def test_wrong_accept_header(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we raise an error when `Accept` header is wrong."""
    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/javascript',
        },
        data=json.dumps({'username': 'sobolevn'}),
    )

    response = _UsernameController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'value_error',
                'loc': [],
                'msg': (
                    'Value error, Cannot serialize response body with '
                    'accepted types [<MediaType: application/javascript>], '
                    "expected=['application/json']"
                ),
                'input': '',
                'ctx': {
                    'error': (
                        'Cannot serialize response body with '
                        'accepted types [<MediaType: application/javascript>], '
                        "expected=['application/json']"
                    ),
                },
            },
        ],
    })


def test_no_content_type_header(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures we handle cases where there's no content_type."""
    username = faker.name()
    request = dmr_rf.post(
        '/whatever/',
        data=json.dumps({'username': username}),
    )
    request.META.pop('CONTENT_TYPE')
    request.content_type = None

    response = _UsernameController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == username
