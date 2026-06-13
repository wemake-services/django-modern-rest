import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from dmr import Controller
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi import build_schema
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, path


class _EventA(msgspec.Struct, frozen=True):
    field_a: str


class _EventB(msgspec.Struct, frozen=True):
    field_b: int


class _ControllerWithUnion(Controller[MsgspecSerializer]):
    async def get(self) -> _EventA | _EventB:
        raise NotImplementedError


def test_schema_error_contains_original_error() -> None:
    """Ensures that errors from schema generation are propagated."""
    router = Router(
        'api/v1/',
        [path('/whatever', _ControllerWithUnion.as_view())],
    )

    with pytest.raises(
        UnsolvableAnnotationsError,
        match='Cannot generate OpenAPI schema',
    ) as exc:
        build_schema(router).convert()

    assert isinstance(exc.value.__cause__, TypeError)
    assert 'union' in str(exc.value.__cause__)


def test_schema_error_name() -> None:
    """Ensures that schema name does not error out."""
    assert (
        MsgspecSerializer.schema_generator.schema_name(_EventA | _EventB)
        is None
    )
