from typing import final

import pytest

from django_modern_rest import Controller, compose_controllers
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _AsyncController(Controller[PydanticSerializer]):
    async def get(self) -> str:
        return 'abc'


@final
class _SyncController(Controller[PydanticSerializer]):
    def post(self) -> str:
        return 'xyz'


@final
class _DuplicatePostController(Controller[PydanticSerializer]):
    def post(self) -> str:
        return 'xyz'


def test_compose_async_and_sync() -> None:
    """Ensures that you can't compose sync and async controllers."""
    msg = 'async and sync endpoints'
    with pytest.raises(ValueError, match=msg):
        compose_controllers(_AsyncController, _SyncController)
    with pytest.raises(ValueError, match=msg):
        compose_controllers(_SyncController, _AsyncController)


def test_compose_zero_controllers() -> None:
    """Ensure that controllers with the overlapping methods can't be used."""
    with pytest.raises(ValueError, match='post'):
        compose_controllers(_DuplicatePostController, _SyncController)
    with pytest.raises(ValueError, match='post'):
        compose_controllers(_SyncController, _DuplicatePostController)
