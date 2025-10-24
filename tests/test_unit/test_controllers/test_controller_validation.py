from http import HTTPStatus
from typing import ClassVar

import pytest

from django_modern_rest import (
    AsyncMetaMixin,
    Controller,
    MetaMixin,
    ResponseDescription,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.validation import ControllerValidator


def test_controller_either_sync_or_async() -> None:
    """Ensure that controllers can have either sync or async endpoints."""
    with pytest.raises(
        EndpointMetadataError,
        match='either be all sync or all async',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            def get(self) -> str:
                raise NotImplementedError

            async def post(self) -> list[str]:
                raise NotImplementedError


def test_controller_duplicate_responses() -> None:
    """Ensure that controllers can't have duplicate status code."""
    with pytest.raises(
        EndpointMetadataError,
        match='403',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            responses: ClassVar[list[ResponseDescription]] = [
                ResponseDescription(int, status_code=HTTPStatus.FORBIDDEN),
                ResponseDescription(str, status_code=HTTPStatus.FORBIDDEN),
            ]

            def get(self) -> str:  # needs at least one endpoint to validate
                raise NotImplementedError


def test_controller_http_spec() -> None:
    """Ensure that controllers with NO_CONTENT must not have bodies."""
    with pytest.raises(
        EndpointMetadataError,
        match='None',
    ):

        class _MixedController(Controller[PydanticSerializer]):
            responses: ClassVar[list[ResponseDescription]] = [
                ResponseDescription(int, status_code=HTTPStatus.NO_CONTENT),
            ]

            def get(self) -> str:  # needs at least one endpoint to validate
                raise NotImplementedError


def test_controller_have_either_mixins() -> None:
    """Ensure that controllers does not have both mixins."""
    with pytest.raises(
        EndpointMetadataError,
        match='can only have one of',
    ):

        class _MixedController(
            AsyncMetaMixin,
            MetaMixin,
            Controller[PydanticSerializer],
        ):
            async def post(self) -> list[str]:
                raise NotImplementedError


def test_controller_have_valid_mixins() -> None:
    """Ensure that controller have a valid mixin."""

    class _MixedSyncController(
        MetaMixin,
        Controller[PydanticSerializer],
    ):
        def post(self) -> list[str]:
            raise NotImplementedError

    class _MixedAsyncController(
        AsyncMetaMixin,
        Controller[PydanticSerializer],
    ):
        async def post(self) -> list[str]:
            raise NotImplementedError


def test_sync_controller_have_invalid_mixin(monkeypatch) -> None:
    """Ensure that sync controller have an invalid mixin."""
    monkeypatch.setattr(
        ControllerValidator,
        '_validate_endpoints',
        lambda self, controller: False,
    )
    with pytest.raises(
        EndpointMetadataError,
        match='contains incompatible mixin',
    ):

        class _MixedSyncController(
            AsyncMetaMixin,
            Controller[PydanticSerializer],
        ):
            def post(self) -> list[str]:
                raise NotImplementedError


def test_async_controller_have_invalid_mixin(monkeypatch) -> None:
    """Ensure that async controller have an invalid mixin."""
    monkeypatch.setattr(
        ControllerValidator,
        '_validate_endpoints',
        lambda self, controller: True,
    )
    with pytest.raises(
        EndpointMetadataError,
        match='contains incompatible mixin',
    ):

        class _MixedAsyncController(
            MetaMixin,
            Controller[PydanticSerializer],
        ):
            async def post(self) -> list[str]:
                raise NotImplementedError
