import json
from http import HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse

from django_modern_rest import (
    AsyncMetaMixin,
    Controller,
    MetaMixin,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _MetaController(
    MetaMixin,
    Controller[PydanticSerializer],
):
    """All body of these methods are not correct."""

    def put(self) -> str:
        raise NotImplementedError

    def post(self) -> str:
        raise NotImplementedError

    def not_a_method(self) -> str:
        raise NotImplementedError


def test_meta_sync(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that sync meta mixin works."""
    assert 'options' in _MetaController.api_endpoints

    request = dmr_rf.options('/whatever/', data={})

    response = _MetaController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.headers == {
        'Allow': 'OPTIONS, POST, PUT',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) is None


@final
class _AsyncMetaController(
    AsyncMetaMixin,
    Controller[PydanticSerializer],
):
    """All body of these methods are not correct."""

    async def get(self) -> str:
        raise NotImplementedError

    async def delete(self) -> str:
        raise NotImplementedError

    async def _post(self) -> str:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_meta_async(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """Ensures that async meta mixin works."""
    assert 'options' in _AsyncMetaController.api_endpoints

    request = dmr_async_rf.options('/whatever/', data={})

    response = await dmr_async_rf.wrap(_AsyncMetaController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.headers == {
        'Allow': 'DELETE, GET, OPTIONS',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) is None
