import json
from http import HTTPStatus
from typing import final

import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot

from django_modern_rest import (
    Blueprint,
    Controller,
    HeaderSpec,
    NewHeader,
    ResponseSpec,
    modify,
)
from django_modern_rest.cookies import CookieSpec
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.errors import ErrorModel, wrap_handler
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
    """Ensures `@modify` can't be used with `HeaderSpec`."""
    with pytest.raises(EndpointMetadataError, match='HeaderSpec'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                headers={'Authorization': HeaderSpec()},  # type: ignore[dict-item]
            )
            def get(self) -> int:
                raise NotImplementedError


def test_modify_with_cookie_description() -> None:
    """Ensures `@modify` can't be used with `CookieSpec`."""
    with pytest.raises(EndpointMetadataError, match='CookieSpec'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                cookies={'test': CookieSpec(required=True)},  # type: ignore[dict-item]
            )
            def get(self) -> int:
                raise NotImplementedError


def test_modify_duplicate_statuses() -> None:
    """Ensures `@modify` can't have duplicate status codes."""
    with pytest.raises(EndpointMetadataError, match='different metadata'):

        class _DuplicateStatuses(Controller[PydanticSerializer]):
            @modify(
                extra_responses=[
                    ResponseSpec(int, status_code=HTTPStatus.OK),
                    ResponseSpec(str, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError


def test_modify_deduplicate_statuses() -> None:
    """Ensures `@modify` same duplicate status codes."""

    class _Blueprint(Blueprint[PydanticSerializer]):
        responses = (
            # From components:
            ResponseSpec(int, status_code=HTTPStatus.OK),
            ResponseSpec(
                dict[str, str],
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
        )

        def post(self) -> str:
            raise NotImplementedError

    class _DeduplicateStatuses(Controller[PydanticSerializer]):
        blueprints = (_Blueprint,)
        responses = (
            # From components:
            ResponseSpec(int, status_code=HTTPStatus.OK),
        )

        @modify(
            extra_responses=[
                # From middleware:
                ResponseSpec(int, status_code=HTTPStatus.OK),
                ResponseSpec(int, status_code=HTTPStatus.OK),
            ],
        )
        def get(self) -> int:
            raise NotImplementedError

    endpoints = _DeduplicateStatuses.api_endpoints
    assert endpoints['GET'].metadata.responses == snapshot({
        HTTPStatus.OK: ResponseSpec(
            return_type=int,
            status_code=HTTPStatus.OK,
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })
    assert endpoints['POST'].metadata.responses == snapshot({
        HTTPStatus.CREATED: ResponseSpec(
            return_type=str,
            status_code=HTTPStatus.CREATED,
        ),
        HTTPStatus.OK: ResponseSpec(
            return_type=int,
            status_code=HTTPStatus.OK,
        ),
        HTTPStatus.PAYMENT_REQUIRED: ResponseSpec(
            return_type=dict[str, str],
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })


def test_modify_modified_in_responses() -> None:
    """Ensures `@modify` can't have duplicate status codes."""
    with pytest.raises(EndpointMetadataError, match='different metadata'):

        class _DuplicateDifferentReturns(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                extra_responses=[
                    ResponseSpec(str, status_code=HTTPStatus.OK),
                ],
            )
            def get(self) -> int:
                raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='different metadata'):

        class _DuplicateDifferentHeaders(Controller[PydanticSerializer]):
            @modify(
                extra_responses=[
                    ResponseSpec(
                        str,
                        status_code=HTTPStatus.OK,
                        headers={'Accept': HeaderSpec()},
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
                controller: Controller[PydanticSerializer],
                exc: Exception,
            ) -> HttpResponse:
                raise NotImplementedError

            @modify(  # type: ignore[deprecated]
                status_code=HTTPStatus.OK,
                error_handler=wrap_handler(endpoint_error),
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
                controller: Controller[PydanticSerializer],
                exc: Exception,
            ) -> HttpResponse:
                raise NotImplementedError

            @modify(  # type: ignore[type-var]
                status_code=HTTPStatus.OK,
                error_handler=wrap_handler(async_endpoint_error),
            )
            def get(self) -> int:
                raise NotImplementedError


@pytest.mark.parametrize(
    'header_name',
    [
        'Set-Cookie',
        'set-cookie',
        'SET-COOKIE',
    ],
)
def test_modify_with_set_cookie(header_name: str) -> None:
    """@modify with Set-Cookie in headers= raise EndpointMetadataError."""
    with pytest.raises(EndpointMetadataError, match=header_name):

        class _SetCookieHeaderController(Controller[PydanticSerializer]):
            @modify(
                status_code=HTTPStatus.OK,
                headers={header_name: NewHeader(value='session=abc123')},
            )
            def post(self) -> dict[str, str]:
                return {'result': 'done'}  # pragma: no cover
