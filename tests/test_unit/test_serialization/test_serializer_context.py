import pydantic
import pytest
from django.test import RequestFactory

from django_modern_rest import Controller, Query
from django_modern_rest.exceptions import RequestSerializationError
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _QueryModel(pydantic.BaseModel):
    age: int


class _TestController(Controller[PydanticSerializer], Query[_QueryModel]):
    """Reusable test controller."""


def test_validation_error_with_invalid_data() -> None:
    """Test that validation errors are properly raised."""
    ctx = _TestController._serializer_context  # noqa: SLF001
    rf = RequestFactory()
    request = rf.get('/whatever/?wrong=1')

    with pytest.raises(RequestSerializationError) as ctx_exc:
        ctx.parse_and_bind(_TestController(), request)

    errors = ctx_exc.value.args[0]  # noqa: WPS441
    assert isinstance(errors, list)


def test_serializer_context_call_method() -> None:  # noqa: WPS432
    """Test that __call__ method validates context correctly."""
    ctx = _TestController._serializer_context  # noqa: SLF001

    # Test successful validation
    validated = ctx({'parsed_query': {'age': 25}})
    assert validated['parsed_query'].age == 25  # noqa: WPS432

    # Test validation error
    with pytest.raises(RequestSerializationError):
        ctx({'parsed_query': {'age': 'not_a_number'}})
