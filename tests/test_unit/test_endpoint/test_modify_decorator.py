import json
from http import HTTPStatus
from typing import ClassVar, final

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from django_modern_rest import (
    Controller,
    Endpoint,
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
    with pytest.raises(EndpointMetadataError, match='different metadata'):

        class _DuplicateStatuses(Controller[PydanticSerializer]):
            @modify(
                extra_responses=[
                    ResponseDescription(int, status_code=HTTPStatus.OK),
                    ResponseDescription(str, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError


def test_modify_deduplicate_statuses() -> None:
    """Ensures `@modify` same duplicate status codes."""

    class _DeduplicateStatuses(Controller[PydanticSerializer]):
        responses: ClassVar[list[ResponseDescription]] = [
            # From components:
            ResponseDescription(int, status_code=HTTPStatus.OK),
        ]

        @modify(
            extra_responses=[
                # From middleware:
                ResponseDescription(int, status_code=HTTPStatus.OK),
                ResponseDescription(int, status_code=HTTPStatus.OK),
            ],
        )
        def get(self) -> int:
            raise NotImplementedError

    endpoint = _DeduplicateStatuses.api_endpoints['GET']
    assert len(endpoint.metadata.responses) == 1


def test_modify_modified_in_responses() -> None:
    """Ensures `@modify` can't have duplicate status codes."""
    with pytest.raises(EndpointMetadataError, match='different metadata'):

        class _DuplicateDifferentReturns(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                extra_responses=[
                    ResponseDescription(str, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='different metadata'):

        class _DuplicateDifferentHeaders(Controller[PydanticSerializer]):
            @modify(
                extra_responses=[
                    ResponseDescription(
                        str,
                        status_code=HTTPStatus.OK,
                        headers={'Accept': HeaderDescription()},
                    ),
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


def test_modify_sync_error_handler_for_async() -> None:
    """Ensure that it is impossible to pass sync error handler to async case."""
    with pytest.raises(EndpointMetadataError, match=' sync `error_handler`'):

        class _WrongModifyController(Controller[PydanticSerializer]):
            def endpoint_error(
                self,
                endpoint: Endpoint,
                exc: Exception,
            ) -> HttpResponse:
                raise NotImplementedError

            @modify(  # type: ignore[deprecated]
                status_code=HTTPStatus.OK,
                error_handler=endpoint_error,
            )
            async def post(self) -> int:
                raise NotImplementedError


def test_modify_async_endpoint_error_for_sync() -> None:
    """Ensure that it is impossible to pass async error handler to sync case."""
    with pytest.raises(EndpointMetadataError, match='async `error_handler`'):

        class _WrongModifyController(Controller[PydanticSerializer]):
            async def async_endpoint_error(
                self,
                endpoint: Endpoint,
                exc: Exception,
            ) -> HttpResponse:
                raise NotImplementedError

            @modify(  # type: ignore[type-var]
                status_code=HTTPStatus.OK,
                error_handler=async_endpoint_error,
            )
            def get(self) -> int:
                raise NotImplementedError
