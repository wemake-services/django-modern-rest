import json
from http import HTTPMethod, HTTPStatus
from typing import final

import pydantic
import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import Controller, rest
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

    @rest(return_type=dict[str, int])
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
    assert json.loads(response.content)['detail'] == snapshot("""\
1 validation error for str
  Input should be a valid string \
[type=string_type, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.12/v/string_type\
""")
