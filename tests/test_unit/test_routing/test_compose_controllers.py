from http import HTTPStatus
from typing import Any, ClassVar, final

import pytest
from django.http import HttpRequest, HttpResponse

from django_modern_rest import (
    Controller,
    ResponseDescription,
    compose_controllers,
    validate,
)
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
        return 'abc'


@final
class _SyncController(Controller[PydanticSerializer]):
    def post(self) -> str:
        return 'xyz'


@final
class _DuplicatePostController(Controller[PydanticSerializer]):
    def post(self) -> str:
        return 'xyz'


@final
class _ZeroMethodsController(Controller[PydanticSerializer]):
    """Just a placeholder."""


@final
class _DifferentSerializer(BaseSerializer):  # type: ignore[misc]
    optimizer: ClassVar[type[BaseEndpointOptimizer]] = PydanticEndpointOptimizer


@final
class _DifferentSerializerController(Controller[_DifferentSerializer]):
    def get(self) -> str:
        return 'xyz'


def test_compose_async_and_sync() -> None:
    """Ensures that you can't compose sync and async controllers."""
    msg = 'async and sync endpoints'
    with pytest.raises(ValueError, match=msg):
        compose_controllers(_AsyncController, _SyncController)
    with pytest.raises(ValueError, match=msg):
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


@final
class _ControllerWithOptions(Controller[PydanticSerializer]):
    @validate(ResponseDescription(str, status_code=HTTPStatus.OK))
    def get(self) -> HttpResponse:
        return HttpResponse(b'GET')

    @validate(ResponseDescription(None, status_code=HTTPStatus.NO_CONTENT))
    def options(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        return HttpResponse(b'OPTIONS')


@final
class _ControllerWithOptions2(Controller[PydanticSerializer]):
    @validate(ResponseDescription(str, status_code=HTTPStatus.OK))
    def post(self) -> HttpResponse:
        return HttpResponse(b'POST')

    @validate(ResponseDescription(None, status_code=HTTPStatus.NO_CONTENT))
    def options(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        return HttpResponse(b'OPTIONS')


def test_compose_controllers_with_options() -> None:
    """Test that controllers with options methods can be composed."""
    # Both controllers have options methods, but composition should work
    # because OPTIONS methods are excluded from composition in routing.py
    composed = compose_controllers(
        _ControllerWithOptions,
        _ControllerWithOptions2,
    )

    # Verify that both controllers have options endpoints
    assert 'options' in _ControllerWithOptions.api_endpoints
    assert 'options' in _ControllerWithOptions2.api_endpoints

    # Verify that composition works (OPTIONS methods are excluded from composition)
    # This is the expected behavior - OPTIONS methods are excluded from composition
    # to avoid conflicts between multiple controllers with OPTIONS methods
    assert composed is not None
