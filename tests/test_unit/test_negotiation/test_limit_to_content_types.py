import json
from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from typing import Any, final

import pydantic
import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import APIError, Controller, Query, ResponseSpec
from dmr.negotiation import ContentType
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer, Renderer
from dmr.test import DMRRequestFactory


class _FakeJson5Renderer(Renderer):
    content_type = 'application/json5'

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any],
    ) -> bytes:
        return JsonRenderer().render(
            to_serialize,
            serializer_hook=serializer_hook,
        )

    @property
    @override
    def validation_parser(self) -> JsonParser:
        return JsonParser()


@final
class _QueryModel(pydantic.BaseModel):
    conflict: bool = False


@final
class _LimitedContentController(
    Query[_QueryModel],
    Controller[PydanticSerializer],
):
    renderers = (JsonRenderer(), _FakeJson5Renderer())

    responses = (
        ResponseSpec(
            int,
            status_code=HTTPStatus.CONFLICT,
            limit_to_content_types={ContentType.json},
        ),
        ResponseSpec(
            int,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            limit_to_content_types={'application/json5'},
        ),
    )

    def get(self) -> int:
        if self.parsed_query.conflict:
            raise APIError(1, status_code=HTTPStatus.CONFLICT)
        raise APIError(2, status_code=HTTPStatus.PAYMENT_REQUIRED)

    def delete(self) -> HttpResponse:
        if self.parsed_query.conflict:
            raise APIError(1, status_code=HTTPStatus.CONFLICT)
        raise APIError(2, status_code=HTTPStatus.PAYMENT_REQUIRED)


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.DELETE,
    ],
)
def test_correctly_limited(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that correct content type works."""
    request = dmr_rf.generic(
        str(method),
        '/whatever/?conflict=1',
        headers={
            'Accept': str(ContentType.json),
        },
    )

    response = _LimitedContentController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CONFLICT, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot(1)


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.DELETE,
    ],
)
def test_wrong_limited(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that wrong content type raises."""
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        headers={
            'Accept': 'application/json',
        },
    )

    response = _LimitedContentController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Response 402 is not allowed for '
                    "'application/json', only for ['application/json5']"
                ),
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.DELETE,
    ],
)
def test_wrong_limited_json5(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that wrong content type raises."""
    request = dmr_rf.generic(
        str(method),
        '/whatever/?conflict=1',
        headers={
            'Accept': 'application/json5',
        },
    )

    response = _LimitedContentController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == {'Content-Type': 'application/json5'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    "Response 409 is not allowed for 'application/json5', "
                    "only for ['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })
