import json
from http import HTTPStatus
from typing import final

import pydantic
from dirty_equals import IsStr
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _MyPydanticModel(pydantic.BaseModel):
    age: int


@final
class _WrongPydanticBodyController(
    Controller[PydanticSerializer],
    Body[_MyPydanticModel],
):
    def post(self) -> str:
        raise NotImplementedError


def test_body_parse_wrong_content_type(rf: RequestFactory) -> None:
    """Ensures that body can't be parsed with wrong content type."""
    request = rf.post(
        '/whatever/',
        data={'age': 1},
        headers={'Content-Type': 'application/xml'},
    )

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': ([
            {
                'type': 'value_error',
                'loc': [],
                'msg': (
                    'Value error, Cannot parse request body with content '
                    "type 'application/xml', expected 'application/json'"
                ),
                'input': '',
                'ctx': {
                    'error': (
                        'Cannot parse request body with content '
                        "type 'application/xml', expected 'application/json'"
                    ),
                },
            },
        ]),
    })


def test_body_parse_wrong_content_type_async(
    dmr_async_rf: DMRRequestFactory,
) -> None:
    """Ensures that async body can't be parsed with wrong content type."""
    request = dmr_async_rf.post(
        '/whatever/',
        data={'age': 1},
        headers={'Content-Type': 'application/xml'},
    )

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': ([
            {
                'type': 'value_error',
                'loc': [],
                'msg': IsStr,
                'input': '',
                'ctx': {
                    'error': IsStr,
                },
            },
        ]),
    })


def test_body_parse_invalid_json(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that body can't be parsed with invalid json."""
    request = dmr_rf.post(
        '/whatever/',
        data=b'{...',
    )

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': ([
            {
                'type': 'value_error',
                'loc': [],
                'msg': IsStr,
                'input': '',
                'ctx': {
                    'error': IsStr,
                },
            },
        ]),
    })
