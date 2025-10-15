import json
from http import HTTPMethod, HTTPStatus
from typing import Generic, TypeVar, final

import pytest
from django.http import HttpResponse

from django_modern_rest import Controller, validate
from django_modern_rest.exceptions import MissingEndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory

_InnerT = TypeVar('_InnerT')


@final
class _CustomResponse(HttpResponse, Generic[_InnerT]):
    """We need to be sure that ``-> _CustomResponse[str]`` also works."""


class _CustomResponseController(Controller[PydanticSerializer]):
    @validate(return_type=str, status_code=HTTPStatus.OK)
    def get(self) -> _CustomResponse[str]:
        return _CustomResponse[str](b'"abc"')

    @validate(return_type=str, status_code=HTTPStatus.OK)
    def post(self) -> _CustomResponse[_InnerT]:  # pyright: ignore[reportInvalidTypeVarUse]
        return _CustomResponse[_InnerT](b'"abc"')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
    ],
)
def test_validate_generic_response_subtype(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _CustomResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.content), str)


def test_validate_required_for_responses() -> None:
    """Ensures `@validate` is required for `HttpResponse` returns."""
    with pytest.raises(MissingEndpointMetadataError, match='@validate'):

        class _NoDecorator(Controller[PydanticSerializer]):
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_validate_on_non_response() -> None:
    """Ensures `@validate` can't be used on regular return types."""
    with pytest.raises(MissingEndpointMetadataError, match='@validate'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @validate(  # type: ignore[type-var]
                return_type=str,
                status_code=HTTPStatus.OK,
            )
            def get(self) -> str:
                raise NotImplementedError
