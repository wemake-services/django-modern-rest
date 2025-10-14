import json
from http import HTTPMethod, HTTPStatus
from typing import TypeAlias, final

import pydantic
import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import Controller, validate
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


@final
class _MyTypedDict(TypedDict):
    missing: str


@final
class _WrongController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct."""

    def get(self) -> str:
        """Does not respect a simple builtin type."""
        return 1  # type: ignore[return-value]

    def post(self) -> list[str]:
        """Does not respect a generic builtin type."""
        return [1, 2]  # type: ignore[list-item]

    def put(self) -> _MyTypedDict:
        """Does not respect a TypedDict type."""
        return {'missing': 1}  # type: ignore[typeddict-item]

    def patch(self) -> _MyPydanticModel:
        """Does not respect a pydantic model type."""
        return {'wrong': 'abc'}  # type: ignore[return-value]

    @validate(return_type=dict[str, int], status_code=HTTPStatus.OK)
    def delete(self) -> HttpResponse:
        """Does not respect a `return_type` validator."""
        return HttpResponse(b'[]')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
        HTTPMethod.DELETE,
    ],
)
def test_validate_response(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response validation works for default settings."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content)['detail']


def test_validate_response_text(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response validation works for default settings."""
    request = dmr_rf.get('/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'string_type',
                'loc': [],
                'msg': 'Input should be a valid string',
                'input': 1,
            },
        ],
    })


@final
class _WrongStatusCodeController(Controller[PydanticSerializer]):
    @validate(return_type=list[int], status_code=HTTPStatus.CREATED)
    def get(self) -> HttpResponse:
        """Does not respect a `status_code` validator."""
        return HttpResponse(b'[]', status=HTTPStatus.OK)


def test_validate_status_code(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.get('/whatever/')

    response = _WrongStatusCodeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': (
            'response.status_code=200 does not match expected 201 status code'
        ),
    })


_ListOfInts: TypeAlias = list[int]


@final
class _StringifiedController(Controller[PydanticSerializer]):
    def get(self) -> '_ListOfInts':
        """Needs to solve the string annotation correctly."""
        return [1, 2]


def test_solve_string_annotation_for_endpoint(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.get('/whatever/')

    response = _StringifiedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == [1, 2]


@final
class _WeakTypeController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct without coercing."""

    def post(self) -> list[int]:
        """Does not respect a generic builtin type."""
        return ['1', '2']  # type: ignore[list-item]


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
    ],
)
def test_weak_type_response_validation(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures weak type response validation does not work."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WeakTypeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'int_type',
                'loc': [0],
                'msg': 'Input should be a valid integer',
                'input': '1',
            },
            {
                'type': 'int_type',
                'loc': [1],
                'msg': 'Input should be a valid integer',
                'input': '2',
            },
        ],
    })
