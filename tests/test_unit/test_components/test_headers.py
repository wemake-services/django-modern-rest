import json
from http import HTTPStatus
from typing import ClassVar, final

import pydantic
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller, Headers
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _SplitCommasModel(pydantic.BaseModel):
    __dmr_split_commas__: ClassVar[frozenset[str]] = frozenset(('x-tag',))

    tags: list[str] = pydantic.Field(alias='X-tag')


@final
class _SplitCommasController(Controller[PydanticSerializer]):
    def get(
        self,
        parsed_headers: Headers[_SplitCommasModel],
    ) -> _SplitCommasModel:
        return parsed_headers


def test_tags_split_commas(dmr_rf: DMRRequestFactory) -> None:
    """Ensures headers can be split on commas."""
    request = dmr_rf.get(
        '/whatever/',
        headers={'x-tag': 'first,second'},
    )

    response = _SplitCommasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == snapshot({
        'X-tag': ['first', 'second'],
    })


@final
class _RegularModel(pydantic.BaseModel):
    # This is here on purpose to test empty sets:
    __dmr_split_commas__: ClassVar[frozenset[str]] = frozenset()

    tags: str = pydantic.Field(alias='X-tag')


@final
class _RegularController(Controller[PydanticSerializer]):
    def get(
        self,
        parsed_headers: Headers[_RegularModel],
    ) -> _RegularModel:
        return parsed_headers


def test_tags_regular(dmr_rf: DMRRequestFactory) -> None:
    """Ensures headers can be regular strings."""
    request = dmr_rf.get(
        '/whatever/',
        headers={'x-tag': 'first,second'},
    )

    response = _RegularController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == snapshot({
        'X-tag': 'first,second',
    })
