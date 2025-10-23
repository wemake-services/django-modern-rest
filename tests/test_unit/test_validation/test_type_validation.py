import sys
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal

import pytest
from django.http import HttpResponse
from typing_extensions import TypedDict

from django_modern_rest import Controller, ResponseDescription, validate
from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer

serializers: list[Any] = [PydanticSerializer]

try:
    from django_modern_rest.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # do nothing then :(  # noqa: WPS420
else:
    # 3.14 does not fully support msgspec yet:
    if sys.version_info < (3, 14):  # pragma: no cover
        serializers.append(MsgspecSerializer)


def _build_annotation(typ: Any) -> Callable[..., Any]:
    def get(self: Any) -> typ:  # pyright: ignore[reportInvalidTypeForm]
        raise NotImplementedError

    return get


def _build_rest(typ: Any) -> Callable[..., Any]:
    @validate(
        ResponseDescription(return_type=typ, status_code=HTTPStatus.OK),
    )
    def get(self: Any) -> HttpResponse:
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
        get = validator_builder(typ)

    endpoint = _Controller.api_endpoints['get']
    validator = endpoint.response_validator

    assert HTTPStatus.OK in endpoint.metadata.responses
    validator._validate_body(  # noqa: SLF001
        raw_data,
        endpoint.metadata.responses[HTTPStatus.OK],
    )


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
        get = validator_builder(typ)

    endpoint = _Controller.api_endpoints['get']
    validator = endpoint.response_validator

    assert HTTPStatus.OK in endpoint.metadata.responses
    with pytest.raises(ResponseSerializationError, match='type'):
        validator._validate_body(  # noqa: SLF001
            raw_data,
            endpoint.metadata.responses[HTTPStatus.OK],
        )
