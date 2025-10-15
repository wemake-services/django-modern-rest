from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal

import pytest
from django.http import HttpResponse

from django_modern_rest import validate
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.plugins.pydantic import PydanticSerializer


def _build_annotation(typ: Any) -> Callable[..., Any]:
    def get() -> typ:  # pyright: ignore[reportInvalidTypeForm]
        raise NotImplementedError

    return get


def _build_rest(typ: Any) -> Callable[..., Any]:
    @validate(return_type=typ, status_code=HTTPStatus.OK)
    def get() -> HttpResponse:
        raise NotImplementedError

    return get


@pytest.mark.parametrize(
    ('typ', 'raw_data'),
    [
        (dict[str, int], {'a': 1}),
        (list[Literal[1]], [1, 1]),
        (set[int], {1, 2}),
        (frozenset[int], frozenset((1, 2))),
        (bytes, b'abc'),
        (str, 'abc'),
        (tuple[int, str], (1, 'a')),
        (tuple[int, ...], (1, 2, 3, 4)),
    ],
)
@pytest.mark.parametrize(
    'validator_builder',
    [
        _build_annotation,
        _build_rest,
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

    validator.validate_content(raw_data)


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
