import json
from http import HTTPStatus
from typing import Final, final

import django
import pydantic
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory

#: `HttpRequest.accepted_types` only drops `q=0` media types since Django 5.2,
#: older versions report them, even though nothing is acceptable.
_ZERO_QUALITY_TYPES: Final = (
    '[]' if django.VERSION >= (5, 2) else '[<MediaType: application/json; q=0>]'
)


@final
class _UncalledController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError  # must not be called


@final
class _EchoController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'echo'


def test_wrong_accept_header(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we raise an error when `Accept` header is wrong."""
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Accept': 'wrong',
        },
    )

    response = _UncalledController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Cannot serialize response body with accepted types '
                    "[<MediaType: wrong>], supported=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


def test_wrong_accept_header_with_content_type(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we raise an error when `Accept` header is wrong."""
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'wrong',
        },
    )

    response = _UncalledController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Cannot serialize response body with accepted '
                    "types [<MediaType: wrong>], supported=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


def test_zero_quality_accept_header(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that `q=0` in `Accept` means "not acceptable"."""
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Accept': 'application/json;q=0',
        },
    )

    response = _UncalledController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': (
                    'Cannot serialize response body with accepted types '
                    f"{_ZERO_QUALITY_TYPES}, supported=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    }


def test_out_of_range_quality_accept_header(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that out of range `q` values do not break negotiation."""
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Accept': 'text/html;q=inf,application/json',
        },
    )

    response = _EchoController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'echo'


@final
class _RequestModel(pydantic.BaseModel):
    username: str


@final
class _UsernameController(
    Controller[PydanticSerializer],
):
    def post(self, parsed_body: Body[_RequestModel]) -> str:
        return parsed_body.username


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
