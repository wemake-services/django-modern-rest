from http import HTTPStatus
from typing import Any, ClassVar

import pytest
from typing_extensions import override

from django_modern_rest import (
    AsyncMetaMixin,
    Controller,
    Endpoint,
    MetaMixin,
    ResponseDescription,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer


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
        match="'AsyncMetaMixin'",
    ):

        class _MixedController(  # type: ignore[misc]
            AsyncMetaMixin,
            MetaMixin,
            Controller[PydanticSerializer],
        ):
            async def post(self) -> list[str]:
                raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match="'MetaMixin'",
    ):

        class _MixedController2(  # type: ignore[misc]
            MetaMixin,
            AsyncMetaMixin,
            Controller[PydanticSerializer],
        ):
            def post(self) -> list[str]:
                raise NotImplementedError


def test_sync_controller_async_error_handler() -> None:
    """Ensure sync controllers cannot override handle_async_error."""
    with pytest.raises(
        EndpointMetadataError,
        match=r'Use `handle_error` instead for sync endpoints.',
    ):

        class _BadController(Controller[PydanticSerializer]):
            @override
            async def handle_async_error(
                self,
                endpoint: Endpoint,
                exc: Exception,
            ) -> Any:
                raise NotImplementedError

            def post(self) -> str:
                raise NotImplementedError


def test_async_controller_sync_error_handler() -> None:
    """Ensure async controllers cannot override handle_error."""
    with pytest.raises(
        EndpointMetadataError,
        match=r'Use `handle_async_error` instead for async endpoints.',
    ):

        class _BadController(Controller[PydanticSerializer]):
            @override
            def handle_error(
                self,
                endpoint: Endpoint,
                exc: Exception,
            ) -> Any:
                raise NotImplementedError

            async def post(self) -> str:
                raise NotImplementedError


def test_sync_controller_sync_error_handler() -> None:
    """Ensure sync error handler works with sync endpoint."""

    class _GoodSyncController(Controller[PydanticSerializer]):
        @override
        def handle_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        def post(self) -> str:
            raise NotImplementedError


def test_async_controller_async_error_handler() -> None:
    """Ensure async error handler works with async endpoint."""

    class _GoodAsyncController(Controller[PydanticSerializer]):
        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        async def post(self) -> str:
            raise NotImplementedError
