import json
from collections.abc import Iterator, Sequence
from http import HTTPStatus
from typing import (
    ClassVar,
    TypeAlias,
    final,
    override,
)

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from django_modern_rest import (
    Blueprint,
    Body,
    Controller,
    modify,
)
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import clear_settings_cache
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _ErrorBody(pydantic.BaseModel):
    error: int


class _ErrorHandlingBlueprint(Blueprint[PydanticSerializer], Body[_ErrorBody]):
    def error_handler(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ValueError):
            return self.to_response('endpoint', status_code=HTTPStatus.OK)
        raise exc

    @modify(error_handler=error_handler, status_code=HTTPStatus.OK)
    def post(self) -> str:  # noqa: WPS238
        if self.parsed_body.error == 0:
            raise ValueError
        if self.parsed_body.error == 1:
            raise TypeError
        if self.parsed_body.error == 2:
            raise KeyError
        if self.parsed_body.error == 3:
            raise IndexError
        raise RuntimeError('unhandled')

    @override
    def handle_error(self, endpoint: Endpoint, exc: Exception) -> HttpResponse:
        if isinstance(exc, TypeError):
            return self.to_response('blueprint', status_code=HTTPStatus.OK)
        raise exc


_BlueprintT: TypeAlias = type[Blueprint[BaseSerializer]]


class _ErrorHandlingController(Controller[PydanticSerializer]):
    blueprints: ClassVar[Sequence[_BlueprintT]] = [_ErrorHandlingBlueprint]

    @override
    def handle_error(self, endpoint: Endpoint, exc: Exception) -> HttpResponse:
        if isinstance(exc, KeyError):
            return self.to_response('controller', status_code=HTTPStatus.OK)
        raise exc

    def put(self) -> str:
        raise TypeError('put')


def _global_handle_error(
    controller: Controller[BaseSerializer],
    endpoint: Endpoint,
    exc: Exception,
) -> HttpResponse:
    if isinstance(exc, IndexError):
        return controller.to_response('global', status_code=HTTPStatus.OK)
    raise exc


@pytest.fixture(autouse=True)
def _settings(settings: LazySettings) -> Iterator[None]:
    clear_settings_cache()
    settings.DMR_SETTINGS = {'global_error_handler': _global_handle_error}
    yield
    clear_settings_cache()


@pytest.mark.parametrize(
    ('error', 'expected'),
    [
        (0, 'endpoint'),
        (1, 'blueprint'),
        (2, 'controller'),
        (3, 'global'),
        (4, RuntimeError),
    ],
)
def test_error_handler_tower(
    dmr_rf: DMRRequestFactory,
    *,
    error: int,
    expected: str | type[Exception],
) -> None:
    """Ensures that error handling tower works."""
    request = dmr_rf.post('/whatever/', data={'error': error})

    if isinstance(expected, str):
        response = _ErrorHandlingController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK
        assert json.loads(response.content) == expected
    else:
        with pytest.raises(expected, match='unhandled'):
            _ErrorHandlingController.as_view()(request)


def test_error_handler_ignored_blueprint(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that error handling tower works."""
    request = dmr_rf.put('/whatever/', data={'error': 0})

    with pytest.raises(TypeError, match='put'):
        _ErrorHandlingController.as_view()(request)


class _AsyncErrorHandlingBlueprint(
    Blueprint[PydanticSerializer],
    Body[_ErrorBody],
):
    async def error_handler(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ValueError):
            return self.to_response('endpoint', status_code=HTTPStatus.OK)
        raise exc

    @modify(error_handler=error_handler, status_code=HTTPStatus.OK)
    async def post(self) -> str:  # noqa: WPS238
        if self.parsed_body.error == 0:
            raise ValueError
        if self.parsed_body.error == 1:
            raise TypeError
        if self.parsed_body.error == 2:
            raise KeyError
        if self.parsed_body.error == 3:
            raise IndexError
        raise RuntimeError('unhandled')

    @override
    async def handle_async_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, TypeError):
            return self.to_response('blueprint', status_code=HTTPStatus.OK)
        raise exc


class _AsyncErrorHandlingController(Controller[PydanticSerializer]):
    blueprints: ClassVar[Sequence[_BlueprintT]] = [_AsyncErrorHandlingBlueprint]

    @override
    async def handle_async_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, KeyError):
            return self.to_response('controller', status_code=HTTPStatus.OK)
        raise exc

    async def put(self) -> str:
        raise TypeError('put')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('error', 'expected'),
    [
        (0, 'endpoint'),
        (1, 'blueprint'),
        (2, 'controller'),
        (3, 'global'),
        (4, RuntimeError),
    ],
)
async def test_error_async_handler_tower(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    error: int,
    expected: str | type[Exception],
) -> None:
    """Ensures that async error handling tower works."""
    request = dmr_async_rf.post('/whatever/', data={'error': error})

    if isinstance(expected, str):
        response = await dmr_async_rf.wrap(
            _AsyncErrorHandlingController.as_view()(request),
        )

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK
        assert json.loads(response.content) == expected
    else:
        with pytest.raises(expected, match='unhandled'):
            await dmr_async_rf.wrap(
                _AsyncErrorHandlingController.as_view()(request),
            )


@pytest.mark.asyncio
async def test_error_async_handler_ignored_blueprint(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async error handling tower works."""
    request = dmr_async_rf.put('/whatever/', data={'error': 0})

    with pytest.raises(TypeError, match='put'):
        await dmr_async_rf.wrap(
            _AsyncErrorHandlingController.as_view()(request),
        )
