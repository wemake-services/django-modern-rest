import json
from http import HTTPMethod, HTTPStatus

import pytest
from django.http import HttpResponse

from django_modern_rest import (
    APIError,
    Controller,
    HeaderDescription,
    ResponseDescription,
    modify,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


class _ValidAPIError(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )
    def get(self) -> HttpResponse:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @modify(
        status_code=HTTPStatus.OK,
        extra_responses=[
            ResponseDescription(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
        ],
    )
    def post(self) -> str:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @modify(status_code=HTTPStatus.PAYMENT_REQUIRED)
    def put(self) -> int:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_valid_api_error(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures validation can validate api errors."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _ValidAPIError.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == 1


class _InvalidAPIError(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.PAYMENT_REQUIRED)
    def post(self) -> str:
        """Type mismatch."""
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @validate(
        ResponseDescription(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )
    def put(self) -> HttpResponse:
        """Status code mismatch."""
        raise APIError(1, status_code=HTTPStatus.UNAUTHORIZED)

    @validate(
        ResponseDescription(
            int,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            headers={'X-API': HeaderDescription()},
        ),
    )
    def patch(self) -> HttpResponse:
        """Headers mismatch."""
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @validate(
        ResponseDescription(
            int,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        ),
    )
    def delete(self) -> HttpResponse:
        """Headers mismatch."""
        raise APIError(
            1,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            headers={'X-API': '1'},
        )


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
        HTTPMethod.DELETE,
    ],
)
def test_api_error_invalid(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures validation can find invalid api errors."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _InvalidAPIError.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content)['detail']


class _InvalidDisabledAPIError(Controller[PydanticSerializer]):
    @modify(validate_responses=False)
    async def get(self) -> str:
        """Type mismatch, but works."""
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)


@pytest.mark.asyncio
async def test_api_error_invalid_disabled(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures validation for api errors can be disabled."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _InvalidDisabledAPIError.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == 1
