import json
from http import HTTPStatus
from typing import cast

from django.http import HttpResponse
from inline_snapshot import snapshot

from django_modern_rest import (
    Controller,
    ResponseSpec,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _HeadController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(None, status_code=HTTPStatus.OK),
        allow_custom_http_methods=True,
    )
    def head(self) -> HttpResponse:
        return self.to_response(None, status_code=HTTPStatus.OK)


def test_head_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `head` method is supported."""
    request = dmr_rf.head('/whatever/')

    response = cast(HttpResponse, _HeadController.as_view()(request))

    assert response.status_code == HTTPStatus.OK
    assert response.content == b'null'


class _GetController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(None, status_code=HTTPStatus.OK),
        allow_custom_http_methods=True,
    )
    def get(self) -> HttpResponse:
        raise NotImplementedError


def test_no_explicit_head_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `get` is not used as an alias for `head`."""
    request = dmr_rf.head('/whatever/')

    response = cast(HttpResponse, _GetController.as_view()(request))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert json.loads(response.content) == snapshot({
        'detail': "Method 'HEAD' is not allowed, allowed: ['GET']",
    })
