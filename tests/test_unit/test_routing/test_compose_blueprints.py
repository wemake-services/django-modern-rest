from collections.abc import Callable
from http import HTTPStatus
from typing import Any, ClassVar, TypeAlias, final

import pytest
from typing_extensions import override

from django_modern_rest import (
    Blueprint,
    Controller,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.metadata import ResponseSpec
from django_modern_rest.options_mixins import AsyncMetaMixin, MetaMixin
from django_modern_rest.plugins.pydantic import (
    PydanticEndpointOptimizer,
    PydanticSerializer,
)
from django_modern_rest.routing import compose_blueprints
from django_modern_rest.serializer import (
    BaseEndpointOptimizer,
    BaseSerializer,
)
from django_modern_rest.validation import BlueprintValidator

BlueprintTuple: TypeAlias = tuple[type[Blueprint[PydanticSerializer]], ...]


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
    default_error_model = dict


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


@pytest.mark.parametrize(
    'blueprints',
    [
        (_AsyncBlueprint, _SyncBlueprint),
        (_SyncBlueprint, _AsyncBlueprint),
    ],
)
def test_compose_async_and_sync(blueprints: BlueprintTuple) -> None:
    """Ensures that you can't compose sync and async controllers."""
    msg = 'all sync or all async'
    with pytest.raises(EndpointMetadataError, match=msg):
        compose_blueprints(*blueprints)


@pytest.mark.parametrize(
    'blueprints',
    [
        (_DuplicatePostBlueprint, _SyncBlueprint),
        (_SyncBlueprint, _DuplicatePostBlueprint),
    ],
)
def test_compose_overlapping_controllers(blueprints: BlueprintTuple) -> None:
    """Ensure that controllers with the overlapping methods can't be used."""
    with pytest.raises(EndpointMetadataError, match='POST'):
        compose_blueprints(*blueprints)


@pytest.mark.parametrize(
    'blueprints',
    [
        (_DifferentSerializerBlueprint, _SyncBlueprint),
        (_SyncBlueprint, _DifferentSerializerBlueprint),
        (_GetBlueprint, _DifferentSerializerBlueprint),
        (_DifferentSerializerBlueprint, _GetBlueprint),
        (_GetBlueprint, _PostBlueprint, _DifferentSerializerBlueprint),
        (_DifferentSerializerBlueprint, _GetBlueprint, _PostBlueprint),
    ],
)
def test_compose_different_serializers(blueprints: BlueprintTuple) -> None:
    """Ensure that controllers with different serializers can't be composed."""
    with pytest.raises(
        EndpointMetadataError,
        match='blueprints with different serializer',
    ):
        compose_blueprints(*blueprints)


@pytest.mark.parametrize(
    'blueprints',
    [
        (_ZeroMethodsBlueprint, _SyncBlueprint),
        (_SyncBlueprint, _ZeroMethodsBlueprint),
    ],
)
def test_compose_controller_no_endpoints(blueprints: BlueprintTuple) -> None:
    """Ensure that controller with no endpoints can't be composed."""
    with pytest.raises(EndpointMetadataError, match='at least one'):
        compose_blueprints(*blueprints)


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
            blueprints = (_SyncBlueprint,)

            def post(self) -> list[int]:
                raise NotImplementedError


def test_compose_blueprints_with_responses() -> None:
    """Ensure that composed controller do not share responses."""

    class _FirstBlueprint(Blueprint[PydanticSerializer]):
        responses = (ResponseSpec(int, status_code=HTTPStatus.CREATED),)

        def get(self) -> list[int]:
            raise NotImplementedError

    class _SecondBlueprint(Blueprint[PydanticSerializer]):
        responses = (ResponseSpec(str, status_code=HTTPStatus.ACCEPTED),)

        def put(self) -> list[int]:
            raise NotImplementedError

    class _ThirdBlueprint(Blueprint[PydanticSerializer]):
        responses = (ResponseSpec(None, status_code=HTTPStatus.NO_CONTENT),)

        def patch(self) -> list[int]:
            raise NotImplementedError

    composed = compose_blueprints(
        _FirstBlueprint,
        _SecondBlueprint,
        _ThirdBlueprint,
    )
    assert isinstance(composed.responses, list)
    for endpoint, description in composed.api_endpoints.items():
        assert len(description.metadata.responses) == 3, endpoint
        assert HTTPStatus.NOT_ACCEPTABLE in description.metadata.responses
        assert HTTPStatus.OK in description.metadata.responses


# Tests specifically for validation edge cases and preventing duplication.
@pytest.mark.parametrize(
    ('blueprints', 'expected_message_part'),
    [
        (
            (_GetBlueprint, _DifferentSerializerBlueprint),
            'blueprints with different serializer',
        ),
        ((_GetBlueprint, _DuplicateGetBlueprint), 'GET'),
        ((_ZeroMethodsBlueprint, _GetBlueprint), 'at least one'),
    ],
)
def test_compose_validation_error_messages(
    blueprints: BlueprintTuple,
    expected_message_part: str,
) -> None:
    """Ensure that validation error messages are descriptive and helpful."""
    with pytest.raises(EndpointMetadataError) as exc_info:
        compose_blueprints(*blueprints)

    assert expected_message_part in str(exc_info.value)


def test_compose_sync_async_no_method_conflict() -> None:
    """Ensure sync/async mix raises error even without method conflict."""
    with pytest.raises(EndpointMetadataError, match='all sync or all async'):
        compose_blueprints(_GetBlueprint, _PostBlueprint, _AsyncPutBlueprint)


@pytest.mark.parametrize(
    'blueprints',
    [
        (_AsyncOptionsBlueprint, _AsyncGetBlueprint),
        (_OptionsBlueprint, _GetBlueprint),
    ],
)
def test_compose_options_conflict_with_meta_mixin(
    blueprints: BlueprintTuple,
) -> None:
    """Ensure that composing OptionsController with MetaMixin works."""
    composed = compose_blueprints(*blueprints)

    assert 'OPTIONS' in composed.api_endpoints
    assert 'GET' in composed.api_endpoints


@pytest.fixture
def make_validated_blueprint() -> Callable[
    [],
    type[BlueprintValidator],
]:  # pragma: no cover
    """Factory fixture that builds a Blueprint with its own Validator."""

    def _factory() -> type[BlueprintValidator]:
        class _Validator(BlueprintValidator):
            call_count: ClassVar[int] = 0

            @override
            def __call__(
                self: Any,
                blueprint: type[Blueprint[BaseSerializer]],
            ) -> None:
                self.__class__.call_count += 1
                return super().__call__(blueprint)

        return _Validator

    return _factory


def test_compose_no_double_validation(
    make_validated_blueprint: Callable[[], type[BlueprintValidator]],
) -> None:
    """Ensure blueprints are not validated twice in compose_blueprints."""
    validator_cls = make_validated_blueprint()
    _GetBlueprint.blueprint_validator_cls = validator_cls
    _PostBlueprint.blueprint_validator_cls = validator_cls
    initial_count = validator_cls.call_count  # type: ignore[attr-defined]
    composed = compose_blueprints(_GetBlueprint, _PostBlueprint)

    assert validator_cls.call_count == initial_count  # type: ignore[attr-defined]
    assert 'POST' in composed.api_endpoints
    assert 'GET' in composed.api_endpoints
