from http import HTTPStatus
from typing import ClassVar, final

import pytest
from typing_extensions import override

from django_modern_rest import (
    Blueprint,
    Controller,
)
from django_modern_rest.controller import BlueprintsT
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.options_mixins import AsyncMetaMixin, MetaMixin
from django_modern_rest.plugins.pydantic import (
    PydanticEndpointOptimizer,
    PydanticSerializer,
)
from django_modern_rest.response import ResponseSpec
from django_modern_rest.routing import compose_blueprints
from django_modern_rest.serialization import (
    BaseEndpointOptimizer,
    BaseSerializer,
)
from django_modern_rest.validation import BlueprintValidator


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


@final
class _GetBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


@final
class _PostBlueprint(Blueprint[PydanticSerializer]):
    def post(self) -> str:
        raise NotImplementedError


@final
class _DuplicateGetBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


@final
class _AsyncGetBlueprint(Blueprint[PydanticSerializer]):
    async def get(self) -> str:
        raise NotImplementedError


@final
class _AsyncPutBlueprint(Blueprint[PydanticSerializer]):
    async def put(self) -> str:
        raise NotImplementedError


@final
class _OptionsBlueprint(MetaMixin, Blueprint[PydanticSerializer]):
    """Controller with OPTIONS method via MetaMixin."""


@final
class _AsyncOptionsBlueprint(AsyncMetaMixin, Blueprint[PydanticSerializer]):
    """Controller with OPTIONS method via AsyncMetaMixin."""


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
        responses: ClassVar[list[ResponseSpec]] = [
            ResponseSpec(int, status_code=HTTPStatus.CREATED),
        ]

        def get(self) -> list[int]:
            raise NotImplementedError

    class _SecondBlueprint(Blueprint[PydanticSerializer]):
        responses: ClassVar[list[ResponseSpec]] = [
            ResponseSpec(str, status_code=HTTPStatus.ACCEPTED),
        ]

        def put(self) -> list[int]:
            raise NotImplementedError

    class _ThirdBlueprint(Blueprint[PydanticSerializer]):
        responses: ClassVar[list[ResponseSpec]] = [
            ResponseSpec(None, status_code=HTTPStatus.NO_CONTENT),
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


# Tests specifically for validation edge cases and preventing duplication.
def test_compose_validation_order_independence() -> None:
    """Ensure validation works regardless of blueprint order."""
    with pytest.raises(EndpointMetadataError, match='different serializer'):
        compose_blueprints(_GetBlueprint, _DifferentSerializerBlueprint)

    with pytest.raises(EndpointMetadataError, match='different serializer'):
        compose_blueprints(_DifferentSerializerBlueprint, _GetBlueprint)

    with pytest.raises(EndpointMetadataError, match='different serializer'):
        compose_blueprints(
            _GetBlueprint,
            _PostBlueprint,
            _DifferentSerializerBlueprint,
        )

    with pytest.raises(EndpointMetadataError, match='different serializer'):
        compose_blueprints(
            _DifferentSerializerBlueprint,
            _GetBlueprint,
            _PostBlueprint,
        )


def test_compose_validation_error_messages() -> None:
    """Ensure that validation error messages are descriptive and helpful."""
    with pytest.raises(EndpointMetadataError) as exc_info:
        compose_blueprints(_GetBlueprint, _DifferentSerializerBlueprint)
    assert 'different serializer' in str(exc_info.value)

    # This is different from test_compose_overlapping_controllers
    # as it tests GET instead of POST.
    with pytest.raises(EndpointMetadataError) as exc_info:
        compose_blueprints(_GetBlueprint, _DuplicateGetBlueprint)
    assert 'GET' in str(exc_info.value)

    # This is different from test_compose_controller_no_endpoints
    # as it uses _ZeroMethodsBlueprint with _GetBlueprint.
    with pytest.raises(EndpointMetadataError) as exc_info:
        compose_blueprints(_ZeroMethodsBlueprint, _GetBlueprint)
    assert 'at least one' in str(exc_info.value)


def test_compose_sync_async_no_method_conflict() -> None:
    """Ensure sync/async mix raises error even without method conflict."""
    with pytest.raises(EndpointMetadataError, match='all sync or all async'):
        compose_blueprints(_GetBlueprint, _PostBlueprint, _AsyncPutBlueprint)


def test_compose_options_conflict_with_meta_mixin() -> None:
    """Ensure that composing OptionsController with MetaMixin works."""
    composed_async = compose_blueprints(
        _AsyncOptionsBlueprint,
        _AsyncGetBlueprint,
    )

    assert 'OPTIONS' in composed_async.api_endpoints
    assert 'GET' in composed_async.api_endpoints

    composed_sync = compose_blueprints(
        _OptionsBlueprint,
        _GetBlueprint,
    )

    assert 'OPTIONS' in composed_sync.api_endpoints
    assert 'GET' in composed_sync.api_endpoints


def test_compose_no_double_validation() -> None:
    """Ensure blueprints are not validated twice in compose_blueprints."""

    class _TrackingValidator1(BlueprintValidator):
        call_count: ClassVar[int] = 0

        @override
        def __call__(
            self,
            blueprint: type[Blueprint[PydanticSerializer]],
        ) -> None:
            self.__class__.call_count += 1
            return super().__call__(blueprint)

    class _TrackingValidator2(BlueprintValidator):
        call_count: ClassVar[int] = 0

        @override
        def __call__(
            self,
            blueprint: type[Blueprint[PydanticSerializer]],
        ) -> None:
            self.__class__.call_count += 1
            return super().__call__(blueprint)

    class _TestBlueprint1(Blueprint[PydanticSerializer]):
        blueprint_validator_cls: ClassVar[type[BlueprintValidator]] = (
            _TrackingValidator1
        )

        def get(self) -> str:
            raise NotImplementedError

    class _TestBlueprint2(Blueprint[PydanticSerializer]):
        blueprint_validator_cls: ClassVar[type[BlueprintValidator]] = (
            _TrackingValidator2
        )

        def post(self) -> str:
            raise NotImplementedError

    initial_count1 = _TrackingValidator1.call_count
    initial_count2 = _TrackingValidator2.call_count

    composed = compose_blueprints(_TestBlueprint1, _TestBlueprint2)

    assert _TrackingValidator1.call_count == initial_count1
    assert _TrackingValidator2.call_count == initial_count2
    assert 'GET' in composed.api_endpoints
    assert 'POST' in composed.api_endpoints
