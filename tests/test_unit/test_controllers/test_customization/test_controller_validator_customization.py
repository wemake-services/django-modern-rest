from typing import ClassVar, final

from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.validation import ControllerValidator


def test_custom_controller_validator_cls() -> None:
    """Ensure we can customize the controller validator factory."""

    @final
    class _ControllerValidatorSubclass(ControllerValidator):
        was_called: ClassVar[bool] = False

        @override
        def __call__(
            self,
            controller: type[Controller[BaseSerializer]],
        ) -> bool | None:
            self.__class__.was_called = True
            return super().__call__(controller)

    @final
    class _CustomValidatorController(Controller[PydanticSerializer]):
        controller_validator_cls: ClassVar[type[ControllerValidator]] = (
            _ControllerValidatorSubclass
        )

    assert _ControllerValidatorSubclass.was_called
