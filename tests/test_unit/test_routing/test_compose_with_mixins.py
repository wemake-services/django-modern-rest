import json
from http import HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse

from django_modern_rest import (
    AsyncMetaMixin,
    Controller,
    MetaMixin,
    compose_controllers,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import (
    PydanticSerializer,
)
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _PostController(Controller[PydanticSerializer]):
    def post(self) -> str:
        return 'xyz'


@final
class _GetController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'xyz'


def test_meta_sync(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that sync meta mixin works."""
    composed = compose_controllers(
        _PostController,
        _GetController,
        meta_mixin=MetaMixin,
    )
    assert 'options' in composed.api_endpoints

    request = dmr_rf.options('/whatever/', data={})

    response = composed.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.headers == {
        'Allow': 'GET, OPTIONS, POST',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) is None


@final
class _AsyncPostController(Controller[PydanticSerializer]):
    async def post(self) -> str:
        return 'xyz'


@final
class _AsyncGetController(Controller[PydanticSerializer]):
    async def get(self) -> str:
        return 'xyz'


@pytest.mark.asyncio
async def test_meta_async(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """Ensures that async meta mixin works."""
    composed = compose_controllers(
        _AsyncPostController,
        _AsyncGetController,
        meta_mixin=AsyncMetaMixin,
    )
    assert 'options' in composed.api_endpoints

    request = dmr_async_rf.options('/whatever/', data={})

    response = await dmr_async_rf.wrap(composed.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.headers == {
        'Allow': 'GET, OPTIONS, POST',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) is None


def test_meta_compose_async_meta_to_sync() -> None:
    """Ensures that async meta mixin cannot be mixed with sync controllers."""
    with pytest.raises(EndpointMetadataError, match='be all sync or all async'):
        compose_controllers(
            _PostController,
            _GetController,
            meta_mixin=AsyncMetaMixin,
        )


def test_meta_compose_sync_meta_to_async() -> None:
    """Ensures that sync meta mixin cannot be mixed with async controllers."""
    with pytest.raises(EndpointMetadataError, match='be all sync or all async'):
        compose_controllers(
            _AsyncPostController,
            _AsyncGetController,
            meta_mixin=MetaMixin,
        )
