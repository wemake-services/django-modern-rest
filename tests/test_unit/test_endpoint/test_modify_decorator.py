import json
from http import HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from django_modern_rest import (
    Controller,
    HeaderDescription,
    NewHeader,
    ResponseDescription,
    modify,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _CustomStatusCodeController(Controller[PydanticSerializer]):
    """Testing the status change."""

    @modify(status_code=HTTPStatus.ACCEPTED)
    def post(self) -> dict[str, str]:
        """Modifies status code from default 201 to custom 202."""
        return {'result': 'done'}


def test_modify_status_code(rf: RequestFactory) -> None:
    """Ensures we can change status code."""
    request = rf.post('/whatever/')

    response = _CustomStatusCodeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {'result': 'done'}


def test_modify_on_response() -> None:
    """Ensures `@modify` can't be used with `HttpResponse` returns."""
    with pytest.raises(EndpointMetadataError, match='@modify'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @modify(  # type: ignore[deprecated]
                status_code=HTTPStatus.OK,
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_modify_with_header_description() -> None:
    """Ensures `@modify` can't be used with `HeaderDescription`."""
    with pytest.raises(EndpointMetadataError, match='HeaderDescription'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                headers={'Authorization': HeaderDescription()},  # type: ignore[dict-item]
            )
            def get(self) -> int:
                raise NotImplementedError


def test_modify_duplicate_statuses() -> None:
    """Ensures `@modify` can't have duplicate status codes."""
    with pytest.raises(EndpointMetadataError, match='200 specified 3 times'):

        class _DuplicateStatuses(Controller[PydanticSerializer]):
            @modify(
                extra_responses=[
                    ResponseDescription(int, status_code=HTTPStatus.OK),
                    ResponseDescription(str, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError


def test_modify_modified_in_responses() -> None:
    """Ensures `@modify` can't have duplicate status codes."""
    with pytest.raises(EndpointMetadataError, match='200 specified 2 times'):

        class _DuplicateExplicitStatuses(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                extra_responses=[
                    ResponseDescription(int, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='200 specified 2 times'):

        class _DuplicateImplicitStatuses(Controller[PydanticSerializer]):
            @modify(
                extra_responses=[
                    ResponseDescription(int, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError


@final
class _CustomHeadersController(Controller[PydanticSerializer]):
    """Testing the headers change."""

    @modify(headers={'X-Test': NewHeader(value='true')})
    def post(self) -> dict[str, str]:
        """Modifies the resulting headers."""
        return {'result': 'done'}


def test_modify_response_headers(rf: RequestFactory) -> None:
    """Ensures we can change headers."""
    request = rf.post('/whatever/')

    response = _CustomHeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers == {
        'Content-Type': 'application/json',
        'X-Test': 'true',
    }
    assert json.loads(response.content) == {'result': 'done'}
