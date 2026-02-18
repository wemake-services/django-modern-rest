from http import HTTPStatus
from typing import final

import pydantic
import pytest
from django.http import HttpResponse
from faker import Faker

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _BodyModel(pydantic.BaseModel):
    email: str


@final
class _MyController(Controller[PydanticSerializer], Body[_BodyModel]):
    def post(self) -> str:
        """Simulates `post` method."""
        return self.parsed_body.email


def test_dmr_rf(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that :class:`dmr.test.DMRRequestFactory` works."""
    email = faker.email()

    request = dmr_rf.post('/whatever/', data={'email': email})
    assert request.body == b'{"email": "%s"}' % email.encode('utf8')

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
    assert request.body == b'{"email": "%s"}' % email.encode('utf8')

    response = _MyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.content == b'"%s"' % email.encode('utf8')


@final
class _MyAsyncController(Controller[PydanticSerializer], Body[_BodyModel]):
    async def post(self) -> str:
        """Simulates `post` method."""
        return self.parsed_body.email


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
    assert request.body == b'{"email": "%s"}' % email.encode('utf8')

    response = await dmr_async_rf.wrap(_MyAsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.content == b'"%s"' % email.encode('utf8')
