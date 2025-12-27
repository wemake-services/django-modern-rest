from http import HTTPStatus
from typing import Any, ClassVar

import pytest
from typing_extensions import override

from django_modern_rest import (
    Blueprint,
    Body,
    Controller,
    Path,
    ResponseSpec,
)
from django_modern_rest.controller import BlueprintsT
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.options_mixins import AsyncMetaMixin, MetaMixin
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.routing import compose_blueprints


class _SyncBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


class _AsyncBlueprint(Blueprint[PydanticSerializer]):
    async def get(self) -> str:
        raise NotImplementedError


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
            responses: ClassVar[list[ResponseSpec]] = [
                ResponseSpec(int, status_code=HTTPStatus.FORBIDDEN),
                ResponseSpec(str, status_code=HTTPStatus.FORBIDDEN),
            ]

            def get(self) -> str:  # needs at least one endpoint to validate
                raise NotImplementedError


@pytest.mark.parametrize(
    'base_class',
    [
        Blueprint[PydanticSerializer],
        Controller[PydanticSerializer],
    ],
)
def test_controller_have_either_mixins(
    *,
    base_class: type[Any],
) -> None:
    """Ensure that controllers does not have both mixins."""
    with pytest.raises(
        EndpointMetadataError,
        match='not both meta mixins',
    ):

        class _MixedController(  # type: ignore[misc]
            AsyncMetaMixin,
            MetaMixin,
            base_class,  # type: ignore[misc]
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
            base_class,  # type: ignore[misc]
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


def test_sync_blueprint_async_error_handler() -> None:
    """Ensure sync blueprints cannot override handle_async_error."""

    class _BadBlueprint(Blueprint[PydanticSerializer]):
        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match='Use `handle_error` instead',
    ):
        compose_blueprints(_BadBlueprint)


def test_async_blueprint_sync_error_handler() -> None:
    """Ensure async blueprints cannot override handle_error."""

    class _BadAsyncBlueprint(Blueprint[PydanticSerializer]):
        @override
        def handle_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        async def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match=r'Use `handle_async_error` instead',
    ):
        compose_blueprints(_BadAsyncBlueprint)


def test_sync_blueprint_sync_error_handler() -> None:
    """Ensure sync error handler works with sync blueprint."""

    class _GoodSyncBlueprint(Blueprint[PydanticSerializer]):
        @override
        def handle_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        def get(self) -> str:
            raise NotImplementedError


def test_async_blueprint_async_error_handler() -> None:
    """Ensure sync error handler works with sync blueprint."""

    class _GoodAsyncBlueprint(Blueprint[PydanticSerializer]):
        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError

        async def get(self) -> str:
            raise NotImplementedError


def test_async_bp_with_sync_handler_fails() -> None:
    """Ensure controllers with async blueprints cannot use sync handle_error."""
    with pytest.raises(
        EndpointMetadataError,
        match='Use `handle_async_error` instead',
    ):

        class _BadController(Controller[PydanticSerializer]):
            blueprints: ClassVar[BlueprintsT] = [
                _AsyncBlueprint,
            ]

            @override
            def handle_error(
                self,
                endpoint: Endpoint,
                exc: Exception,
            ) -> Any:
                raise NotImplementedError


def test_sync_bp_with_async_handler_fails() -> None:
    """Ensure controllers with blueprints cannot use async error handler."""
    with pytest.raises(
        EndpointMetadataError,
        match='Use `handle_error` instead',
    ):

        class _BadController(Controller[PydanticSerializer]):
            blueprints: ClassVar[BlueprintsT] = [
                _SyncBlueprint,
            ]

            @override
            async def handle_async_error(
                self,
                endpoint: Endpoint,
                exc: Exception,
            ) -> Any:
                raise NotImplementedError


def test_async_bp_with_async_handler_ok() -> None:
    """Ensure controllers with async blueprints can use async error handler."""

    class _GoodController(Controller[PydanticSerializer]):
        blueprints: ClassVar[BlueprintsT] = [
            _AsyncBlueprint,
        ]

        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_sync_bp_with_sync_handler_ok() -> None:
    """Ensure controllers with sync blueprints can use sync error handler."""

    class _GoodController(Controller[PydanticSerializer]):
        blueprints: ClassVar[BlueprintsT] = [
            _SyncBlueprint,
        ]

        @override
        def handle_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_bp_no_endpoints_with_async_error_handler() -> None:
    """Ensure BP without endpoints don't trigger error handler validation."""

    class _EmptyBlueprint(Blueprint[PydanticSerializer]):
        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_no_endpoints_with_async_error_handler() -> None:
    """Ensure controller wo endpoints don't trigger error handler validation."""

    class _EmptyController(Controller[PydanticSerializer]):
        @override
        async def handle_async_error(
            self,
            endpoint: Endpoint,
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_bp_no_endpoints_with_error_handler() -> None:
    """Ensure BP without endpoints don't trigger error handler validation."""

    class _EmptyBlueprint(Blueprint[PydanticSerializer]):
        @override
        def handle_error(
            self,
            endpoint: Endpoint,
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
            exc: Exception,
        ) -> Any:
            raise NotImplementedError


def test_no_double_parsing() -> None:
    """Ensure we can't have parsing in both controller and blueprint."""

    class _BadBlueprint(Blueprint[PydanticSerializer], Body[dict[str, str]]):
        def get(self) -> str:
            raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match='put parsing into blueprints',
    ):

        class _BadController(
            Controller[PydanticSerializer],
            Path[dict[str, str]],
        ):
            blueprints = [_BadBlueprint]
