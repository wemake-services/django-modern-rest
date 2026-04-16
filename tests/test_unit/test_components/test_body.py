import json
from http import HTTPStatus
from typing import ClassVar, final

import pydantic
import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot

from dmr import Body, Controller
from dmr.errors import ErrorType
from dmr.parsers import MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _MyPydanticModel(pydantic.BaseModel):
    age: int


@final
class _WrongPydanticBodyController(
    Controller[PydanticSerializer],
):
    def post(self, parsed_body: Body[_MyPydanticModel]) -> str:
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
        'detail': [
            {
                'msg': (
                    'Cannot parse request body with content type '
                    "'application/xml', expected=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


@final
class _WrongAsyncPydanticBodyController(
    Controller[PydanticSerializer],
):
    async def post(self, parsed_body: Body[_MyPydanticModel]) -> str:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_body_parse_wrong_content_type_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async body can't be parsed with wrong content type."""
    request = dmr_async_rf.post(
        '/whatever/',
        data={'age': 1},
        headers={'Content-Type': 'application/xml'},
    )

    response = await dmr_async_rf.wrap(
        _WrongAsyncPydanticBodyController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Cannot parse request body with content type '
                    "'application/xml', expected=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
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
    assert response.headers == {'Content-Type': 'application/json'}
    # This test is executed with both `msgspec` and `json` parsers,
    # so we can't use `snapshot()` here:
    assert (
        json.loads(response.content)['detail'][0]['type']
        == ErrorType.value_error
    )


class _TagsForceList(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('tags', 'simple'))

    simple: list[str]
    tags: list[str | None]
    null: str | None
    regular: str


class _TagsForceListController(
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    def post(self, parsed_body: Body[_TagsForceList]) -> _TagsForceList:
        return parsed_body


def test_body_force_list(rf: RequestFactory) -> None:
    """Ensures that body can use ``__dmr_force_list__``."""
    request = rf.post(
        '/whatever/',
        data={
            'simple': ['foo', 'bar', 'null'],
            'tags': ['foo', 'bar', 'null'],
            'null': 'null',
            'regular': 'null',
        },
    )

    response = _TagsForceListController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'simple': ['foo', 'bar', 'null'],
        'tags': ['foo', 'bar', 'null'],
        'null': 'null',
        'regular': 'null',
    })


class _TagsSplitCommas(pydantic.BaseModel):
    __dmr_split_commas__: ClassVar[frozenset[str]] = frozenset((
        'tags',
        'with_nulls',
    ))
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('with_nulls',))

    tags: list[str]
    with_nulls: list[str | None]


class _TagsSplitCommasController(
    Controller[PydanticSerializer],
):
    parsers = (MultiPartParser(),)

    def post(self, parsed_body: Body[_TagsSplitCommas]) -> _TagsSplitCommas:
        return parsed_body


def test_body_split_commas(rf: RequestFactory) -> None:
    """Ensures that body can use ``__dmr_split_commas__``."""
    request = rf.post(
        '/whatever/',
        data={'tags': 'foo,bar,null', 'with_nulls': 'foo,bar,null'},
    )

    response = _TagsSplitCommasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'tags': ['foo', 'bar', 'null'],
        'with_nulls': ['foo', 'bar', None],
    })
