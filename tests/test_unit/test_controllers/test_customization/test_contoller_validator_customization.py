from typing import ClassVar, final, override

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.validation import ControllerValidator


@final
class _ControllerValidatorSubclass(ControllerValidator):
    """Test that we can replace the default controller validator."""

    # We can add a marker to track if this was called
    was_called: ClassVar[bool] = False

    @override
    def __call__(self, controller: 'type[Controller[BaseSerializer]]') -> bool:
        """Run the validation and mark that it was called."""
        _ControllerValidatorSubclass.was_called = True
        return super().__call__(controller)


@final
class _CustomControllerValidatorController(Controller[PydanticSerializer]):
    controller_validator_cls: ClassVar[type[ControllerValidator]] = (
        _ControllerValidatorSubclass
    )

    def get(self) -> int:
        raise NotImplementedError


def test_custom_controller_validator_cls() -> None:
    """Ensure we can customize the controller validator factory."""
    assert _ControllerValidatorSubclass.was_called is True
    assert _CustomControllerValidatorController._is_async is False  # noqa: SLF001
