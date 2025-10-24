from typing import ClassVar, final

import pytest

from django_modern_rest import (
    Controller,
    MetaMixin,
    compose_controllers,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import (
    PydanticEndpointOptimizer,
    PydanticSerializer,
)
from django_modern_rest.serialization import (
    BaseEndpointOptimizer,
    BaseSerializer,
)


@final
class _AsyncController(Controller[PydanticSerializer]):
    async def get(self) -> str:
        raise NotImplementedError


@final
class _SyncController(Controller[PydanticSerializer]):
    def post(self) -> str:
        raise NotImplementedError


@final
class _DuplicatePostController(Controller[PydanticSerializer]):
    def post(self) -> str:
        raise NotImplementedError


@final
class _ZeroMethodsController(Controller[PydanticSerializer]):
    """Just a placeholder."""


@final
class _DifferentSerializer(BaseSerializer):  # type: ignore[misc]
    optimizer: ClassVar[type[BaseEndpointOptimizer]] = PydanticEndpointOptimizer


@final
class _DifferentSerializerController(Controller[_DifferentSerializer]):
    def get(self) -> str:
        raise NotImplementedError


def test_compose_async_and_sync() -> None:
    """Ensures that you can't compose sync and async controllers."""
    msg = 'all sync or all async'
    with pytest.raises(EndpointMetadataError, match=msg):
        compose_controllers(_AsyncController, _SyncController)
    with pytest.raises(EndpointMetadataError, match=msg):
        compose_controllers(_SyncController, _AsyncController)


def test_compose_overlapping_controllers() -> None:
    """Ensure that controllers with the overlapping methods can't be used."""
    with pytest.raises(ValueError, match='post'):
        compose_controllers(_DuplicatePostController, _SyncController)
    with pytest.raises(ValueError, match='post'):
        compose_controllers(_SyncController, _DuplicatePostController)


def test_compose_different_serializers() -> None:
    """Ensure that controllers with different serializers can't be used."""
    with pytest.raises(ValueError, match='different serializer'):
        compose_controllers(_DifferentSerializerController, _SyncController)
    with pytest.raises(ValueError, match='different serializer'):
        compose_controllers(_SyncController, _DifferentSerializerController)


def test_compose_controller_no_endpoints() -> None:
    """Ensure that controller with no endpoints can't be composed."""
    with pytest.raises(ValueError, match='at least one'):
        compose_controllers(_ZeroMethodsController, _SyncController)
    with pytest.raises(ValueError, match='at least one'):
        compose_controllers(_SyncController, _ZeroMethodsController)


def test_compose_controllers_with_meta() -> None:
    """Ensure that controller with no endpoints can't be composed."""

    @final
    class _OptionsController(MetaMixin, Controller[PydanticSerializer]):
        """Just a placeholder."""

    # Ok:
    compose_controllers(_SyncController, _OptionsController)

    with pytest.raises(ValueError, match='options'):
        compose_controllers(_OptionsController, _OptionsController)
