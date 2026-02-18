import json
from http import HTTPStatus

from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import (
    Controller,
    ResponseSpec,
    validate,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


class _HeadController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(None, status_code=HTTPStatus.OK),
    )
    def head(self) -> HttpResponse:
        return self.to_response(None, status_code=HTTPStatus.OK)


def test_head_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `head` method is supported."""
    request = dmr_rf.head('/whatever/')

    response = _HeadController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.content == b''


class _GetController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(None, status_code=HTTPStatus.OK),
    )
    def get(self) -> HttpResponse:
        raise NotImplementedError


def test_no_explicit_head_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `get` is not used as an alias for `head`."""
    request = dmr_rf.head('/whatever/')

    response = _GetController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': "Method 'HEAD' is not allowed, allowed: ['GET']",
                'type': 'not_allowed',
            },
        ],
    })
