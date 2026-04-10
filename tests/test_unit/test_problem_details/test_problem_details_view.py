import json
from http import HTTPStatus
from typing import Any

import pydantic
import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.urls import path
from inline_snapshot import snapshot
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

from dmr import Controller, Query, ResponseSpec
from dmr.errors import ErrorModel, ErrorType
from dmr.negotiation import ContentType, accepts
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.problem_details import ProblemDetailsError, ProblemDetailsModel
from dmr.renderers import JsonRenderer
from dmr.routing import Router
from dmr.security.django_session import DjangoSessionAsyncAuth
from dmr.test import DMRAsyncRequestFactory


class _QueryModel(pydantic.BaseModel):
    number: int = 0


class _ProblemDetailsController(Controller[PydanticSerializer]):
    renderers = (
        JsonRenderer(ContentType.json),
        JsonRenderer(ContentType.json_problem_details),
    )

    error_model = ProblemDetailsError.error_model({
        ContentType.json: ErrorModel,
    })

    responses = (
        ResponseSpec(error_model, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )

    auth = (DjangoSessionAsyncAuth(),)

    async def get(self, parsed_query: Query[_QueryModel]) -> str:
        raise ProblemDetailsError.conditional_error(
            (
                f'Your current balance is {parsed_query.number}, '
                'but the price is 15'
            ),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            type='https://example.com/probs/out-of-credit',
            title='Not enough funds',
            instance='/account/users/1/',
            extra={'balance': parsed_query.number, 'price': 15},
            controller=self,
        )

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:
        if accepts(self.request, ContentType.json_problem_details):
            return ProblemDetailsError.format_error(
                error,
                loc=loc,
                error_type=error_type,
                title='From format_error',
            )
        return super().format_error(error, loc=loc, error_type=error_type)


async def _resolve(user: User | AnonymousUser) -> User | AnonymousUser:
    return user


@pytest.mark.asyncio
async def test_conditional_error_details(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Test that error details render correctly for conditional types."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Accept': str(ContentType.json_problem_details)},
    )
    request.auser = lambda: _resolve(User())

    response = await dmr_async_rf.wrap(
        _ProblemDetailsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert response.headers == {
        'Content-Type': str(ContentType.json_problem_details),
    }
    assert json.loads(response.content) == snapshot({
        'detail': 'Your current balance is 0, but the price is 15',
        'status': 402,
        'type': 'https://example.com/probs/out-of-credit',
        'title': 'Not enough funds',
        'instance': '/account/users/1/',
        'balance': 0,
        'price': 15,
    })


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'request_headers',
    [
        {},
        {'Accept': str(ContentType.json)},
    ],
)
async def test_problem_details_default_error(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    request_headers: dict[str, str],
) -> None:
    """Test that error details render correctly for conditional types."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers=request_headers,
    )
    request.auser = lambda: _resolve(User())

    response = await dmr_async_rf.wrap(
        _ProblemDetailsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert response.headers == {
        'Content-Type': str(ContentType.json),
    }
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Your current balance is 0, but the price is 15',
                'type': 'https://example.com/probs/out-of-credit',
            },
        ],
    })


@pytest.mark.asyncio
async def test_builtin_error_problem_details(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Test that error details correctly render default errors."""
    request = dmr_async_rf.get(
        '/whatever/?number=a',
        headers={'Accept': str(ContentType.json_problem_details)},
    )
    request.auser = lambda: _resolve(User())

    response = await dmr_async_rf.wrap(
        _ProblemDetailsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {
        'Content-Type': str(ContentType.json_problem_details),
    }
    assert json.loads(response.content) == snapshot({
        'detail': (
            'Input should be a valid integer, unable to '
            'parse string as an integer'
        ),
        'status': 400,
        'type': 'value_error',
        'title': 'From format_error',
    })


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'request_headers',
    [
        {},
        {'Accept': str(ContentType.json)},
    ],
)
async def test_builtin_error_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    request_headers: dict[str, str],
) -> None:
    """Test that error details correctly render default errors."""
    request = dmr_async_rf.get(
        '/whatever/?number=a',
        headers=request_headers,
    )
    request.auser = lambda: _resolve(User())

    response = await dmr_async_rf.wrap(
        _ProblemDetailsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {
        'Content-Type': str(ContentType.json),
    }
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['parsed_query', 'number'],
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.asyncio
async def test_builtin_error_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Test that error details correctly render default errors."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Accept': str(ContentType.json_problem_details)},
    )
    request.auser = lambda: _resolve(AnonymousUser())

    response = await dmr_async_rf.wrap(
        _ProblemDetailsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers == {
        'Content-Type': str(ContentType.json_problem_details),
    }
    assert json.loads(response.content) == snapshot({
        'detail': 'Not authenticated',
        'status': 401,
        'type': 'security',
        'title': 'From format_error',
    })


class _ProblemDetailsDefaultController(Controller[PydanticSerializer]):
    error_model = ProblemDetailsModel

    responses = (
        ResponseSpec(error_model, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )

    async def get(self, parsed_query: Query[_QueryModel]) -> str:
        raise ProblemDetailsError(
            (
                f'Your current balance is {parsed_query.number}, '
                'but the price is 15'
            ),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            type='https://example.com/probs/out-of-credit',
            title='Not enough funds',
            instance='/account/users/1/',
            extra={'balance': parsed_query.number, 'price': 15},
        )

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:
        return ProblemDetailsError.format_error(
            error,
            loc=loc,
            error_type=error_type,
            title='From format_error',
        )


@pytest.mark.asyncio
async def test_problem_details_as_default(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Test that error details can be a default error model."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _ProblemDetailsDefaultController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert response.headers == {'Content-Type': str(ContentType.json)}
    assert json.loads(response.content) == snapshot({
        'detail': 'Your current balance is 0, but the price is 15',
        'status': 402,
        'type': 'https://example.com/probs/out-of-credit',
        'title': 'Not enough funds',
        'instance': '/account/users/1/',
        'balance': 0,
        'price': 15,
    })


@pytest.mark.asyncio
async def test_problem_details_as_default_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Test that error details can be a default error model."""
    request = dmr_async_rf.get('/whatever/?number=a')

    response = await dmr_async_rf.wrap(
        _ProblemDetailsDefaultController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': str(ContentType.json)}
    assert json.loads(response.content) == snapshot({
        'detail': (
            'Input should be a valid integer, unable '
            'to parse string as an integer'
        ),
        'status': 400,
        'type': 'value_error',
        'title': 'From format_error',
    })


class _ProblemDetailsValidationController(Controller[PydanticSerializer]):
    # NOTE: it does not redefine `error_model`, but raises `ProblemDetails`
    responses = (
        ResponseSpec(ErrorModel, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )

    async def get(self, parsed_query: Query[_QueryModel]) -> str:
        raise ProblemDetailsError(
            (
                f'Your current balance is {parsed_query.number}, '
                'but the price is 15'
            ),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'request_headers',
    [
        {},
        {'Accept': str(ContentType.json)},
    ],
)
async def test_problem_details_spec_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    request_headers: dict[str, str],
) -> None:
    """Test that controller validates invalid error models."""
    request = dmr_async_rf.get('/whatever/', headers=request_headers)

    response = await dmr_async_rf.wrap(
        _ProblemDetailsValidationController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert response.headers == {'Content-Type': str(ContentType.json)}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid list',
                'loc': ['detail'],
                'type': 'value_error',
            },
        ],
    })


def test_problem_defaults_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for problem details."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [
                        path(
                            '/with-negotiation',
                            _ProblemDetailsController.as_view(),
                        ),
                        path(
                            '/default',
                            _ProblemDetailsDefaultController.as_view(),
                        ),
                        path(
                            '/regular',
                            _ProblemDetailsValidationController.as_view(),
                        ),
                    ],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
