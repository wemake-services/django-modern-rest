from typing import final

import pytest

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _SyncController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise ZeroDivisionError('custom')


def test_sync_controller_runtime_error(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that runtime errors bubble up."""
    request = dmr_rf.get('/whatever/')

    with pytest.raises(ZeroDivisionError, match='custom'):
        _SyncController.as_view()(request)


@final
class _AsyncController(Controller[PydanticSerializer]):
    async def get(self) -> str:
        raise ZeroDivisionError('custom')


@pytest.mark.asyncio
async def test_async_controller_runtime_error(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that runtime errors bubble up."""
    request = dmr_async_rf.get('/whatever/')

    with pytest.raises(ZeroDivisionError, match='custom'):
        await dmr_async_rf.wrap(_AsyncController.as_view()(request))
