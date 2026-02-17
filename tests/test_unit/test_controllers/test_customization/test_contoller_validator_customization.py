from typing import ClassVar, final

from typing_extensions import override

from dmr import Blueprint, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.validation import BlueprintValidator


def test_custom_blueprint_validator_cls() -> None:
    """Ensure we can customize the blueprint validator factory."""

    @final
    class _BlueprintValidatorSubclass(BlueprintValidator):
        # We can add a marker to track if this was called
        was_called: ClassVar[bool] = False

        @override
        def __call__(self, blueprint: type[Blueprint[BaseSerializer]]) -> None:
            self.__class__.was_called = True
            return super().__call__(blueprint)

    @final
    class _CustomValidatorBlueprint(Blueprint[PydanticSerializer]):
        blueprint_validator_cls: ClassVar[type[BlueprintValidator]] = (
            _BlueprintValidatorSubclass
        )

    assert _BlueprintValidatorSubclass.was_called


def test_custom_controller_validator_cls() -> None:
    """Ensure we can customize the controller validator factory."""

    @final
    class _BlueprintValidatorSubclass(BlueprintValidator):
        # We can add a marker to track if this was called
        was_called: ClassVar[bool] = False

        @override
        def __call__(self, blueprint: type[Blueprint[BaseSerializer]]) -> None:
            self.__class__.was_called = True
            return super().__call__(blueprint)

    @final
    class _CustomValidatorController(Controller[PydanticSerializer]):
        blueprint_validator_cls: ClassVar[type[BlueprintValidator]] = (
            _BlueprintValidatorSubclass
        )

    assert _BlueprintValidatorSubclass.was_called
