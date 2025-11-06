from typing import ClassVar, final

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import SerializerContext


@final
class _SerializerContextSubclass(SerializerContext):
    """Test that we can replace the default serializer context."""


@final
class _CustomSerializerContextController(Controller[PydanticSerializer]):
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        _SerializerContextSubclass
    )

    def get(self) -> int:
        raise NotImplementedError


def test_custom_serializer_context_cls() -> None:
    """Ensure we can customize the serializer context."""
    assert (
        _CustomSerializerContextController.serializer_context_cls
        is _SerializerContextSubclass
    )
    assert isinstance(
        _CustomSerializerContextController._serializer_context,  # noqa: SLF001
        _SerializerContextSubclass,
    )
