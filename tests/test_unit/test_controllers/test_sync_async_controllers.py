import pytest
from django.core.exceptions import ImproperlyConfigured

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer


def test_controller_either_sync_or_async() -> None:
    """Ensure that controllers can have either sync or async endpoints."""
    with pytest.raises(
        ImproperlyConfigured,
        match='either be all sync or all async',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            def get(self) -> str:
                raise NotImplementedError

            async def post(self) -> list[str]:
                raise NotImplementedError
