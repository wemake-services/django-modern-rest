import json
from http import HTTPMethod, HTTPStatus
from typing import Any, Generic, TypeVar

import pytest
from django.core.exceptions import DisallowedRedirect
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from django_modern_rest import (
    APIError,
    Blueprint,
    Controller,
    HeaderSpec,
    ResponseSpec,
    modify,
    validate,
)
from django_modern_rest.components import ComponentParser, Path
from django_modern_rest.cookies import CookieSpec, NewCookie
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.errors import ErrorModel, ErrorType
from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security import AsyncAuth, SyncAuth
from django_modern_rest.serializer import BaseSerializer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


class _ValidAPIError(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            return_type=int,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        ),
    )
    def get(self) -> HttpResponse:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @modify(
        status_code=HTTPStatus.OK,
        extra_responses=[
            ResponseSpec(
                return_type=int,
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
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
        ResponseSpec(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )
    def put(self) -> HttpResponse:
        """Status code mismatch."""
        raise APIError(1, status_code=HTTPStatus.UNAUTHORIZED)

    @validate(
        ResponseSpec(
            int,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            headers={'X-API': HeaderSpec()},
        ),
    )
    def patch(self) -> HttpResponse:
        """Headers mismatch."""
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @validate(
        ResponseSpec(
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


class _ControllerLevelAPIError(Controller[PydanticSerializer]):
    responses = (ResponseSpec(int, status_code=HTTPStatus.PAYMENT_REQUIRED),)

    def get(self) -> str:
        """Type mismatch, but works."""
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)


def test_valid_api_error_contoller_level(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures validation can validate api errors on controllers."""
    endpoint = _ControllerLevelAPIError.api_endpoints['GET']
    assert endpoint.metadata.responses.keys() == {
        HTTPStatus.OK,
        HTTPStatus.PAYMENT_REQUIRED,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }

    request = dmr_rf.get('/whatever/')

    response = _ControllerLevelAPIError.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == 1


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


_StrT = TypeVar('_StrT', bound=str)


class _TestComponent(ComponentParser, Generic[_StrT]):
    context_name = 'test'
    error_message = 'From component'

    @override
    @classmethod
    def provide_context_data(
        cls,
        endpoint: Endpoint,
        blueprint: Blueprint[BaseSerializer],
        *,
        field_model: Any,
    ) -> Any:
        raise APIError(cls.error_message, status_code=HTTPStatus.IM_A_TEAPOT)


class _ControllerWithTestComponent(
    Controller[PydanticSerializer],
    _TestComponent[str],
):
    @modify(
        extra_responses=[
            ResponseSpec(str, status_code=HTTPStatus.IM_A_TEAPOT),
        ],
    )
    def get(self) -> int:
        raise NotImplementedError


def test_raise_api_error_in_component(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures you can raise APIError in a component."""
    request = dmr_rf.get('/whatever/')

    response = _ControllerWithTestComponent.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_A_TEAPOT
    assert json.loads(response.content) == _TestComponent.error_message


class _TestSyncAuth(SyncAuth):
    error_message = 'from auth'

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Any | None:
        raise APIError(self.error_message, status_code=HTTPStatus.IM_A_TEAPOT)

    @property
    @override
    def security_scheme(self) -> Components:
        raise NotImplementedError

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        raise NotImplementedError


class _TestAsyncAuth(AsyncAuth):
    error_message = 'from auth'

    @override
    async def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Any | None:
        raise APIError(self.error_message, status_code=HTTPStatus.IM_A_TEAPOT)

    @property
    @override
    def security_scheme(self) -> Components:
        raise NotImplementedError

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        raise NotImplementedError


class _ControllerWithTestSyncAuth(Controller[PydanticSerializer]):
    @modify(
        auth=[_TestSyncAuth()],
        extra_responses=[
            ResponseSpec(str, status_code=HTTPStatus.IM_A_TEAPOT),
        ],
    )
    def get(self) -> int:
        raise NotImplementedError


def test_raise_api_error_in_sync_auth(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures you can raise APIError in auth."""
    auth = _ControllerWithTestSyncAuth.api_endpoints['GET'].metadata.auth
    assert auth

    request = dmr_rf.get('/whatever/')

    response = _ControllerWithTestSyncAuth.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_A_TEAPOT, response.content
    assert (
        json.loads(response.content) == auth[0].error_message  # type: ignore[union-attr]
    )


class _ControllerWithTestAsyncAuth(Controller[PydanticSerializer]):
    responses = [
        ResponseSpec(str, status_code=HTTPStatus.IM_A_TEAPOT),
    ]
    auth = [_TestAsyncAuth()]

    async def get(self) -> int:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_raise_api_error_in_async_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures you can raise APIError in async auth."""
    auth = _ControllerWithTestAsyncAuth.api_endpoints['GET'].metadata.auth
    assert auth

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _ControllerWithTestAsyncAuth.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_A_TEAPOT, response.content
    assert (
        json.loads(response.content) == auth[0].error_message  # type: ignore[union-attr]
    )


class _ComplexAPIError(Controller[PydanticSerializer]):
    @modify(
        extra_responses=[
            ResponseSpec(ErrorModel, status_code=HTTPStatus.PAYMENT_REQUIRED),
        ],
    )
    def get(self) -> str:
        raise APIError(
            self.format_error(
                'test',
                loc='api',
                error_type=ErrorType.user_msg,
            ),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


def test_valid_complex_api_error(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures validation can validate api errors."""
    request = dmr_rf.get('/whatever/')

    response = _ComplexAPIError.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'test', 'loc': ['api'], 'type': 'user_msg'}],
    })


class _CookieAPIError(Controller[PydanticSerializer]):
    responses = (
        ResponseSpec(
            int,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            cookies={'error_id': CookieSpec()},
        ),
    )

    def get(self) -> str:
        """Type mismatch, but works."""
        raise APIError(
            1,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            cookies={'error_id': NewCookie(value='value')},
        )


def test_api_error_with_cookies(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures validation can validate api errors."""
    request = dmr_rf.get('/whatever/')

    response = _CookieAPIError.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert json.loads(response.content) == 1
    assert response.cookies.output() == snapshot(
        'Set-Cookie: error_id=value; Path=/; SameSite=lax',
    )


def test_api_error_redirect_status() -> None:
    """Ensures that we can't create APIError with redirect status code."""
    with pytest.raises(DisallowedRedirect, match='APIRedirectError'):
        APIError('whatever', status_code=HTTPStatus.FOUND)


class _PathResponseController(
    Controller[PydanticSerializer],
    Path[dict[str, str]],
):
    def get(self) -> str:
        raise NotImplementedError


def test_path_component_responses() -> None:
    """Ensures that ``Path`` component adds 404 to the response spec."""
    endpoint = _PathResponseController.api_endpoints['GET']
    assert list(endpoint.metadata.responses.keys()) == snapshot(
        [
            HTTPStatus.OK,
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            HTTPStatus.NOT_ACCEPTABLE,
        ],
    )
