import pytest

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class _Custom(Controller[PydanticSerializer]):
    """Empty."""


def test_http_method_not_allowed() -> None:
    """Ensure that old django method on a controller does not work."""
    controller = _Custom()

    with pytest.raises(
        (DeprecationWarning, NotImplementedError),
        match='handle_method_not_allowed',
    ):
        controller.http_method_not_allowed(None)  # type: ignore[deprecated, arg-type]


def test_controller_options() -> None:
    """Ensure that old OPTIONS django method on a controller does not work."""
    controller = _Custom()

    with pytest.raises(
        (DeprecationWarning, NotImplementedError),
        match='meta',
    ):
        controller.options(None)  # type: ignore[deprecated, arg-type]
