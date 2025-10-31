from http import HTTPStatus
from typing import ClassVar, final

import pytest

from django_modern_rest import (
    Blueprint,
    Controller,
)
from django_modern_rest.controller import BlueprintsT
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.options_mixins import MetaMixin
from django_modern_rest.plugins.pydantic import (
    PydanticEndpointOptimizer,
    PydanticSerializer,
)
from django_modern_rest.response import ResponseDescription
from django_modern_rest.routing import compose_blueprints
from django_modern_rest.serialization import (
    BaseEndpointOptimizer,
    BaseSerializer,
)


@final
class _AsyncBlueprint(Blueprint[PydanticSerializer]):
    async def get(self) -> str:
        raise NotImplementedError


@final
class _SyncBlueprint(Blueprint[PydanticSerializer]):
    def post(self) -> str:
        raise NotImplementedError


@final
class _DuplicatePostBlueprint(Blueprint[PydanticSerializer]):
    def post(self) -> str:
        raise NotImplementedError


@final
class _ZeroMethodsBlueprint(Blueprint[PydanticSerializer]):
    """Just a placeholder."""


@final
class _DifferentSerializer(BaseSerializer):  # type: ignore[misc]
    optimizer: ClassVar[type[BaseEndpointOptimizer]] = PydanticEndpointOptimizer


@final
class _DifferentSerializerBlueprint(Blueprint[_DifferentSerializer]):
    def get(self) -> str:
        raise NotImplementedError


def test_compose_async_and_sync() -> None:
    """Ensures that you can't compose sync and async controllers."""
    msg = 'all sync or all async'
    with pytest.raises(EndpointMetadataError, match=msg):
        compose_blueprints(_AsyncBlueprint, _SyncBlueprint)
    with pytest.raises(EndpointMetadataError, match=msg):
        compose_blueprints(_SyncBlueprint, _AsyncBlueprint)


def test_compose_overlapping_controllers() -> None:
    """Ensure that controllers with the overlapping methods can't be used."""
    with pytest.raises(EndpointMetadataError, match='POST'):
        compose_blueprints(_DuplicatePostBlueprint, _SyncBlueprint)
    with pytest.raises(EndpointMetadataError, match='POST'):
        compose_blueprints(_SyncBlueprint, _DuplicatePostBlueprint)


def test_compose_different_serializers() -> None:
    """Ensure that controllers with different serializers can't be used."""
    with pytest.raises(EndpointMetadataError, match='different serializer'):
        compose_blueprints(_DifferentSerializerBlueprint, _SyncBlueprint)
    with pytest.raises(EndpointMetadataError, match='different serializer'):
        compose_blueprints(_SyncBlueprint, _DifferentSerializerBlueprint)


def test_compose_controller_no_endpoints() -> None:
    """Ensure that controller with no endpoints can't be composed."""
    with pytest.raises(EndpointMetadataError, match='at least one'):
        compose_blueprints(_ZeroMethodsBlueprint, _SyncBlueprint)
    with pytest.raises(EndpointMetadataError, match='at least one'):
        compose_blueprints(_SyncBlueprint, _ZeroMethodsBlueprint)


def test_compose_blueprints_with_meta() -> None:
    """Ensure that controller with no endpoints can't be composed."""

    class _OptionsBlueprint(MetaMixin, Blueprint[PydanticSerializer]):
        """Just a placeholder."""

    # Ok:
    compose_blueprints(_SyncBlueprint, _OptionsBlueprint)
    with pytest.raises(EndpointMetadataError, match='OPTIONS'):
        compose_blueprints(_OptionsBlueprint, _OptionsBlueprint)


def test_compose_with_existing_endpoint() -> None:
    """Check that class-level composition checks for existing endpoints."""
    with pytest.raises(EndpointMetadataError, match='POST'):

        class MyController(Controller[PydanticSerializer]):
            blueprints: ClassVar[BlueprintsT] = [
                _SyncBlueprint,
            ]

            def post(self) -> list[int]:
                raise NotImplementedError


def test_compose_blueprints_with_responses() -> None:
    """Ensure that composed controller do not share responses."""

    class _FirstBlueprint(Blueprint[PydanticSerializer]):
        responses: ClassVar[list[ResponseDescription]] = [
            ResponseDescription(int, status_code=HTTPStatus.CREATED),
        ]

        def get(self) -> list[int]:
            raise NotImplementedError

    class _SecondBlueprint(Blueprint[PydanticSerializer]):
        responses: ClassVar[list[ResponseDescription]] = [
            ResponseDescription(str, status_code=HTTPStatus.ACCEPTED),
        ]

        def put(self) -> list[int]:
            raise NotImplementedError

    class _ThirdBlueprint(Blueprint[PydanticSerializer]):
        responses: ClassVar[list[ResponseDescription]] = [
            ResponseDescription(None, status_code=HTTPStatus.NO_CONTENT),
        ]

        def patch(self) -> list[int]:
            raise NotImplementedError

    composed = compose_blueprints(
        _FirstBlueprint,
        _SecondBlueprint,
        _ThirdBlueprint,
    )
    assert composed.responses == []
    for endpoint, description in composed.api_endpoints.items():
        assert len(description.metadata.responses) == 2, endpoint
