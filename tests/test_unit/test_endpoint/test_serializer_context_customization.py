from typing import ClassVar, final

from dmr import Controller
from dmr.endpoint import Endpoint, SerializerContext
from dmr.plugins.pydantic import PydanticSerializer


@final
class _SerializerContextSubclass(SerializerContext):
    """Test that we can replace the default serializer context."""


@final
class _CustomEndpoint(Endpoint):
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        _SerializerContextSubclass
    )


@final
class _CustomSerializerContextController(Controller[PydanticSerializer]):
    endpoint_cls = _CustomEndpoint

    def get(self) -> int:
        raise NotImplementedError


def test_custom_serializer_context_cls() -> None:
    """Ensure we can customize the serializer context."""
    assert (
        _CustomSerializerContextController.endpoint_cls.serializer_context_cls
        is _SerializerContextSubclass
    )

    context = _CustomSerializerContextController.api_endpoints[
        'GET'
    ]._serializer_context
    assert isinstance(
        context,
        _SerializerContextSubclass,
    )
