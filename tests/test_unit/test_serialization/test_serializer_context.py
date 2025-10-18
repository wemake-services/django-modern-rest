from typing import Any, ClassVar, final

import pydantic
import pytest
from django.test import RequestFactory
from typing_extensions import override

from django_modern_rest import Controller, Query
from django_modern_rest.exceptions import RequestSerializationError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import (
    BaseEndpointOptimizer,
    BaseSerializer,
    SerializerContext,
)


@final
class _BoomOptimizer(BaseEndpointOptimizer):
    @classmethod
    @override
    def optimize_endpoint(cls, metadata: Any) -> None:  # pragma: no cover
        ...


class _BoomSerializer(BaseSerializer):
    """Serializer raising TypeError to test error handling."""

    validation_error: ClassVar[type[Exception]] = ValueError
    optimizer: ClassVar[type[BaseEndpointOptimizer]] = _BoomOptimizer

    @classmethod
    @override
    def to_json(cls, structure: Any) -> bytes:  # pragma: no cover
        return b'{}'

    @classmethod
    @override
    def from_json(cls, buffer: Any) -> Any:  # pragma: no cover
        return buffer

    @classmethod
    @override
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        *,
        strict: bool,
    ) -> Any:
        # Raise TypeError to test TypeError wrapping in SerializerContext
        raise TypeError('boom')

    @classmethod
    @override
    def error_to_json(cls, error: Exception) -> Any:  # pragma: no cover
        return {'detail': str(error)}


@final
class _QueryModel(pydantic.BaseModel):
    age: int


def test_serializer_context_typeerror_is_wrapped() -> None:
    """Ensure TypeError is wrapped into RequestSerializationError."""

    class BoomController(Controller[_BoomSerializer], Query[dict[str, int]]):  # noqa: WPS110
        """Test controller for boom serializer."""

    ctx = SerializerContext.for_controller(BoomController, _BoomSerializer)
    rf = RequestFactory()
    request = rf.get('/whatever/?age=1')

    with pytest.raises(RequestSerializationError) as ctx_exc:
        ctx.parse_and_bind(BoomController(), request)

    assert 'boom' in str(ctx_exc.value)


def test_error_locations_strip_component_prefix() -> None:
    """Ensures top-level component name is stripped from error locations."""

    class PydanticQueryController(  # noqa: WPS110
        Controller[PydanticSerializer],
        Query[_QueryModel],
    ):
        """Controller with pydantic query for error loc test."""

    ctx = SerializerContext.for_controller(
        PydanticQueryController,
        PydanticSerializer,
    )
    rf = RequestFactory()
    request = rf.get('/whatever/?wrong=1')

    with pytest.raises(RequestSerializationError) as ctx_exc:
        ctx.parse_and_bind(PydanticQueryController(), request)

    errors = ctx_exc.value.args[0]  # noqa: WPS441
    assert isinstance(errors, list)
    # Ensure we only have field name without component prefix
    assert errors[0]['loc'][0] == 'age'


def test_error_locations_without_component_prefix_kept_ok() -> None:  # noqa: WPS118
    """Ensure non-component prefixes in loc remain unchanged."""

    class Dummy(Controller[PydanticSerializer], Query[_QueryModel]):  # noqa: WPS110
        """Minimal controller to build context instance."""

    ctx = SerializerContext.for_controller(Dummy, PydanticSerializer)
    # Access internal helper to directly test branch where prefix not matched:
    res = ctx._try_strip_component_prefix(  # noqa: SLF001,WPS110
        [{'loc': ['other', 'field']}],
    )
    assert res[0]['loc'] == ['other', 'field']
