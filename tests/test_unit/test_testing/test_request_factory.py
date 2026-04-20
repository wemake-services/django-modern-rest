from http import HTTPStatus
from typing import final
from unittest.mock import patch

import pydantic
import pytest
from django.http import HttpResponse
from faker import Faker

from dmr import Body, Controller
from dmr.internal.json import _compact_json_dumps
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _BodyModel(pydantic.BaseModel):
    email: str


@final
class _MyController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[_BodyModel]) -> str:
        """Simulates `post` method."""
        return parsed_body.email


def test_encode_json_fallback_without_msgspec(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Check correct encoding when msgspec is unavailable (stdlib fallback)."""
    with patch('dmr.internal.json._json_dumps', _compact_json_dumps):
        request = dmr_rf.post('/whatever/', data={'key': 'value'})
    assert request.body == b'{"key":"value"}'


def test_encode_json_with_list_data(dmr_rf: DMRRequestFactory) -> None:
    """Ensures list data is JSON-encoded via `_DMRMixin._encode_json`."""
    request = dmr_rf.post('/whatever/', data=[1, 2, 3])
    assert request.body == b'[1,2,3]'


def test_dmr_rf(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that :class:`dmr.test.DMRRequestFactory` works."""
    email = faker.email()

    request = dmr_rf.post('/whatever/', data={'email': email})
    assert request.body == b'{"email":"%s"}' % email.encode('utf8')

    response = _MyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.content == b'"%s"' % email.encode('utf8')


def test_dmr_async_rf_to_sync(
    dmr_async_rf: DMRAsyncRequestFactory,
    faker: Faker,
) -> None:
    """
    Ensures that :class:`dmr.test.DMRAsyncRequestFactory` works.

    Fully compatible with ``DMRRequestFactory`` with its API.
    """
    email = faker.email()

    request = dmr_async_rf.post('/whatever/', data={'email': email})
    assert request.body == b'{"email":"%s"}' % email.encode('utf8')

    response = _MyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.content == b'"%s"' % email.encode('utf8')


@final
class _MyAsyncController(Controller[PydanticSerializer]):
    async def post(self, parsed_body: Body[_BodyModel]) -> str:
        """Simulates `post` method."""
        return parsed_body.email


@pytest.mark.asyncio
async def test_dmr_async_rf_to_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    faker: Faker,
) -> None:
    """
    Ensures that :class:`dmr.test.DMRAsyncRequestFactory` works.

    Fully compatible with ``DMRRequestFactory`` with its API.
    """
    email = faker.email()

    request = dmr_async_rf.post('/whatever/', data={'email': email})
    assert request.body == b'{"email":"%s"}' % email.encode('utf8')

    response = await dmr_async_rf.wrap(_MyAsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.content == b'"%s"' % email.encode('utf8')
