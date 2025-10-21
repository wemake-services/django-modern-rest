from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal

import pytest
from django.http import HttpResponse
from typing_extensions import TypedDict

from django_modern_rest import Controller, ResponseDescription, validate
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer

serializers: list[Any] = [PydanticSerializer]

try:
    from django_modern_rest.plugins.msgspec import MsgspecSerializer
except ImportError:
    pass  # do nothing then :(
else:
    serializers.append(MsgspecSerializer)


def _build_annotation(typ: Any) -> Callable[..., Any]:
    def get() -> typ:  # pyright: ignore[reportInvalidTypeForm]
        raise NotImplementedError

    return get


def _build_rest(typ: Any) -> Callable[..., Any]:
    @validate(
        ResponseDescription(return_type=typ, status_code=HTTPStatus.OK),
    )
    def get() -> HttpResponse:
        raise NotImplementedError

    return get


class _TypedDict(TypedDict):
    age: int


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
        (tuple[int, ...], ()),
        (_TypedDict, {'age': 1}),
        (None, None),
        (Any, None),
    ],
)
@pytest.mark.parametrize(
    'validator_builder',
    [
        _build_annotation,
        _build_rest,
    ],
)
@pytest.mark.parametrize(
    'serializer',
    serializers,
)
def test_valid_data(
    *,
    typ: Any,
    raw_data: Any,
    validator_builder: Callable[[Any], Callable[..., Any]],
    serializer: type[BaseSerializer],
) -> None:
    """Ensure that correct data can be validated."""

    class _Controller(Controller[serializer]):  # type: ignore[valid-type]
        """Just a placeholder."""

    validator = Endpoint(
        _build_annotation(typ),
        controller_cls=_Controller,
    ).response_validator

    validator.validate_modification(_Controller(), raw_data)


@pytest.mark.parametrize(
    ('typ', 'raw_data'),
    [
        (dict[str, int], {1: 'a'}),
        (list[Literal[1]], [2]),
        (set[int], {1, 'a'}),
        (frozenset[int], frozenset((1, object()))),
        (bytes, 'abc'),
        (str, b'abc'),
        (tuple[int, str], ('a', 1)),
        (tuple[int, ...], ('a')),
        (_TypedDict, {}),
        (_TypedDict, {'a': 1}),
        (_TypedDict, {'age': 'a'}),
        (None, 1),
    ],
)
@pytest.mark.parametrize(
    'validator_builder',
    [
        _build_annotation,
        _build_rest,
    ],
)
@pytest.mark.parametrize(
    'serializer',
    serializers,
)
def test_invalid_data(
    *,
    typ: Any,
    raw_data: Any,
    validator_builder: Callable[[Any], Callable[..., Any]],
    serializer: type[BaseSerializer],
) -> None:
    """Ensure that correct data can be validated."""

    class _Controller(Controller[serializer]):  # type: ignore[valid-type]
        """Just a placeholder."""

    validator = Endpoint(
        _build_annotation(typ),
        controller_cls=_Controller,
    ).response_validator

    with pytest.raises(ResponseSerializationError):
        validator.validate_modification(_Controller(), raw_data)
