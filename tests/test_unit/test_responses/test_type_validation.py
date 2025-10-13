from collections.abc import Callable
from typing import Any, Literal

import pytest

from django_modern_rest import rest
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.plugins.pydantic import PydanticSerializer


def _build_annotation(typ: Any) -> Callable[..., Any]:
    def factory() -> typ:  # pyright: ignore[reportInvalidTypeForm]
        """Used as an endpoint."""

    return factory


def _build_rest(typ: Any) -> Callable[..., Any]:
    @rest(return_type=typ)
    def factory():  # type: ignore[no-untyped-def]
        """Used as an endpoint."""

    return factory


@pytest.mark.parametrize(
    ('typ', 'raw_data'),
    [
        (dict[str, int], {'a': 1}),
        (list[Literal[1]], [1, 1]),
    ],
)
@pytest.mark.parametrize(
    'validator_builder',
    [
        _build_annotation,
        _build_rest,
        lambda typ: _build_annotation(_build_rest(rest)),
        lambda typ: _build_rest(_build_annotation(rest)),
    ],
)
def test_valid_data(
    *,
    typ: Any,
    raw_data: Any,
    validator_builder: Callable[[Any], Callable[..., Any]],
) -> None:
    """Ensure that correct data can be validated."""
    validator = Endpoint(
        _build_annotation(typ),
        serializer=PydanticSerializer,
    ).response_validator

    assert validator.validate_content(raw_data)


@pytest.mark.parametrize(
    ('typ', 'raw_data'),
    [
        (dict[str, int], {1: 'a'}),
        (list[Literal[1]], [2]),
    ],
)
@pytest.mark.parametrize(
    'validator_builder',
    [
        _build_annotation,
        _build_rest,
        lambda typ: _build_annotation(_build_rest(rest)),
        lambda typ: _build_rest(_build_annotation(rest)),
    ],
)
def test_invalid_data(
    *,
    typ: Any,
    raw_data: Any,
    validator_builder: Callable[[Any], Callable[..., Any]],
) -> None:
    """Ensure that correct data can be validated."""
    validator = Endpoint(
        _build_annotation(typ),
        serializer=PydanticSerializer,
    ).response_validator

    with pytest.raises(ResponseSerializationError):
        validator.validate_content(raw_data)
