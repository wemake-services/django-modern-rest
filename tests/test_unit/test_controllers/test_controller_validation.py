from collections.abc import AsyncIterator, Iterator
from http import HTTPStatus
from typing import Any

import pytest
from typing_extensions import override

from dmr import Controller, ResponseSpec
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.options_mixins import AsyncMetaMixin, MetaMixin
from dmr.plugins.pydantic import PydanticSerializer
from dmr.plugins.pydantic.serializer import PydanticEndpointOptimizer
from dmr.streaming.jsonl import JsonLinesController
from dmr.streaming.sse import SSEController


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
            responses = (
                ResponseSpec(int, status_code=HTTPStatus.FORBIDDEN),
                ResponseSpec(str, status_code=HTTPStatus.FORBIDDEN),
            )

            def get(self) -> str:  # needs at least one endpoint to validate
                raise NotImplementedError


def test_controller_have_either_mixins() -> None:
    """Ensure that controllers does not have both mixins."""
    with pytest.raises(
        EndpointMetadataError,
        match='not both meta mixins',
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
        match='not both meta mixins',
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
        match='Use `handle_error` instead',
    ):

        class _BadController(Controller[PydanticSerializer]):
            @override
            async def handle_async_error(
                self,
                endpoint: Endpoint,
                controller: Controller[PydanticSerializer],
                exc: Exception,
            ) -> Any:
                raise NotImplementedError

            def post(self) -> str:
                raise NotImplementedError


def test_async_controller_sync_error_handler() -> None:
    """Ensure async controllers cannot override handle_error."""
    with pytest.raises(
        EndpointMetadataError,
        match='Use `handle_async_error` instead',
    ):

        class _BadController(Controller[PydanticSerializer]):
            @override
            def handle_error(
                self,
                endpoint: Endpoint,
                controller: Controller[PydanticSerializer],
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
            controller: Controller[PydanticSerializer],
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
            controller: Controller[PydanticSerializer],
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        async def post(self) -> str:
            raise NotImplementedError


def test_no_endpoints_with_async_error_handler() -> None:
    """Ensure controller wo endpoints don't trigger error handler validation."""

    class _EmptyController(Controller[PydanticSerializer]):
        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            controller: Controller[PydanticSerializer],
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_no_endpoints_with_error_handler() -> None:
    """Ensure controller wo endpoints don't trigger error handler validation."""

    class _EmptyController(Controller[PydanticSerializer]):
        @override
        def handle_error(
            self,
            endpoint: Endpoint,
            controller: Controller[PydanticSerializer],
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_endpoint_rejects_async_gen() -> None:
    """Ensure endpoints cannot be async generators."""

    class _NoOpOptimizer(PydanticEndpointOptimizer):
        @override
        @classmethod
        def optimize_endpoint(cls, metadata: Any) -> None:  # noqa: WPS324
            return None  # noqa: WPS324

    class _NoOpPydanticSerializer(PydanticSerializer):
        optimizer = _NoOpOptimizer

    with pytest.raises(
        EndpointMetadataError,
        match='is a generator',
    ):

        class _BadController(Controller[_NoOpPydanticSerializer]):
            async def get(self) -> AsyncIterator[int]:
                yield 1  # pragma: no cover


def test_endpoint_rejects_sync_gen() -> None:
    """Ensure endpoints cannot be sync generators."""

    # We need this to be able to ignore `Iterator[int]` serialization.
    class _NoOpOptimizer(PydanticEndpointOptimizer):
        @override
        @classmethod
        def optimize_endpoint(cls, metadata: Any) -> None:  # noqa: WPS324
            return None  # noqa: WPS324

    class _NoOpPydanticSerializer(PydanticSerializer):
        optimizer = _NoOpOptimizer

    with pytest.raises(
        EndpointMetadataError,
        match='is a generator',
    ):

        class _BadController(Controller[_NoOpPydanticSerializer]):
            def get(self) -> Iterator[int]:
                yield 1  # pragma: no cover


@pytest.mark.parametrize(
    'controller_cls',
    [
        SSEController,
        JsonLinesController,
    ],
)
def test_streaming_controller_async_validation(
    *,
    controller_cls: type[Controller[Any]],
) -> None:
    """Ensure streaming endpoints also cannot be async generators."""
    with pytest.raises(
        EndpointMetadataError,
        match='is a generator',
    ):

        class _BadController(
            controller_cls[PydanticSerializer],  # type: ignore[valid-type, misc]
        ):
            async def get(self) -> AsyncIterator[int]:
                yield 1  # pragma: no cover
