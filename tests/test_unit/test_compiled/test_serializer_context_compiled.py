import os
from types import BuiltinFunctionType, FunctionType
from typing import TYPE_CHECKING

import pytest

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory

if TYPE_CHECKING:
    from tests.test_unit.test_compiled.conftest import CleanModules


def test_correct_import() -> None:
    """Ensure that the default import is correct."""
    from dmr.compiled import empty_serializer_context  # noqa: PLC0415
    from dmr.envs import USE_COMPILED  # noqa: PLC0415

    if USE_COMPILED:  # pragma: no cover
        assert '_pure' not in empty_serializer_context.__module__, USE_COMPILED
    else:  # pragma: no cover
        assert '_pure' in empty_serializer_context.__module__, USE_COMPILED
        assert isinstance(empty_serializer_context, FunctionType)

    with pytest.raises(TypeError, match='missing'):
        empty_serializer_context()  # type: ignore[call-arg]


def test_correct_type() -> None:  # pragma: no cover
    """Ensure that the default import is correct."""
    from dmr.compiled import empty_serializer_context  # noqa: PLC0415

    enabled = os.environ.get('HATCH_BUILD_HOOKS_ENABLE')
    if enabled is None:
        pytest.skip(reason='This test only runs in cibuildwheel')
    assert isinstance(empty_serializer_context, BuiltinFunctionType), enabled


class _Controller(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


@pytest.mark.parametrize('compiled', [True, False])
def test_empty_serializer_context(
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: 'CleanModules',
    dmr_rf: DMRRequestFactory,
    *,
    compiled: bool,
) -> None:
    """Ensure that `empty_serializer_context` works correctly."""
    endpoint = _Controller.api_endpoints['GET']
    controller = _Controller()
    controller.setup(dmr_rf.get('/'))

    # Our setup, it can be compiled or not:
    monkeypatch.setenv('DMR_USE_COMPILED', str(int(compiled)))
    with clean_modules({'dmr.envs', 'dmr.compiled'}):
        from dmr.compiled import empty_serializer_context  # noqa: PLC0415
        from dmr.envs import USE_COMPILED  # noqa: PLC0415

        assert USE_COMPILED is compiled
        if compiled:
            assert '_pure' not in empty_serializer_context.__module__, (
                USE_COMPILED,
                compiled,
            )
        else:
            assert '_pure' in empty_serializer_context.__module__, (
                USE_COMPILED,
                compiled,
            )
            assert isinstance(empty_serializer_context, FunctionType)

        # The function itself:
        assert empty_serializer_context(endpoint, controller) == {}
