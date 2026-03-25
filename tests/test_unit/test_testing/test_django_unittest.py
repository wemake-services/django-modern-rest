import json
from typing import final

import pydantic
from django.http import HttpResponse
from django.test import SimpleTestCase
from typing_extensions import override

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


class _UserModel(pydantic.BaseModel):
    username: str


class _AsyncController(
    Controller[PydanticSerializer],
):
    async def post(self, parsed_body: Body[_UserModel]) -> _UserModel:
        return parsed_body


class _SyncController(
    Controller[PydanticSerializer],
):
    def post(self, parsed_body: Body[_UserModel]) -> _UserModel:
        return parsed_body


@final
class ClientWorksWithRegularTest(SimpleTestCase):
    """Ensure that regular django-style unittests also work."""

    @override
    def setUp(self) -> None:
        self._dmr_rf = DMRRequestFactory()
        self._dmr_async_rf = DMRAsyncRequestFactory()

    async def test_async_controller(self) -> None:
        """Async methods must work."""
        request_data = {'username': 'example'}
        request = self._dmr_async_rf.post('/whatever/', data=request_data)

        response = await self._dmr_async_rf.wrap(
            _AsyncController.as_view()(request),
        )

        assert isinstance(response, HttpResponse)
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == request_data

    def test_sync_controller(self) -> None:
        """Sync methods must work."""
        request_data = {'username': 'example'}
        request = self._dmr_rf.post('/whatever/', data=request_data)

        response = _SyncController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == request_data
