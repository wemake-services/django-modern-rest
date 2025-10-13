from typing import final

import pytest

from django_modern_rest import Controller, compose_controllers, rest
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class AsyncController(Controller[PydanticSerializer]):
    @rest(return_type=str)
    async def get(self) -> str:
        return 'abc'


@final
class SyncController(Controller[PydanticSerializer]):
    @rest(return_type=str)
    def post(self) -> str:
        return 'xyz'


def test_compose_async_and_sync() -> None:
    """Ensures that you can't compose sync and async controllers."""
    msg = 'async and sync endpoints'
    with pytest.raises(ValueError, match=msg):
        compose_controllers(AsyncController, SyncController)
    with pytest.raises(ValueError, match=msg):
        compose_controllers(SyncController, AsyncController)
