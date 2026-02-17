from http import HTTPMethod, HTTPStatus
from typing import Final, final

import pytest
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy

from dmr import (
    APIRedirectError,
    Controller,
    HeaderSpec,
    modify,
    validate,
)
from dmr.metadata import ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_REDIRECT_URL: Final = reverse_lazy(
    'api:jwt_auth:jwt_obtain_access_refresh_sync',
)
_REDIRECT_SPEC: Final = ResponseSpec(
    None,
    status_code=HTTPStatus.FOUND,
    headers={'Location': HeaderSpec()},
)


@final
class _RedirectController(Controller[PydanticSerializer]):
    @validate(_REDIRECT_SPEC)
    def get(self) -> HttpResponse:
        raise APIRedirectError(
            _REDIRECT_URL,
            status_code=HTTPStatus.FOUND,
        )

    @validate(_REDIRECT_SPEC)
    def post(self) -> HttpResponseRedirect:
        return HttpResponseRedirect(
            _REDIRECT_URL,
            content_type='application/json',
        )

    @modify(extra_responses=[_REDIRECT_SPEC])
    def put(self) -> dict[str, str]:
        raise APIRedirectError(
            _REDIRECT_URL,
            status_code=HTTPStatus.FOUND,
        )


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_api_redirect(dmr_rf: DMRRequestFactory, *, method: HTTPMethod) -> None:
    """Ensures we can raise ``APIRedirectError`` in sync endpoint."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _RedirectController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FOUND, response.content
    assert response.headers == {
        'Content-Type': 'application/json',
        'Location': str(_REDIRECT_URL),
    }
    assert response.content == b''


@final
class _AsyncRedirectController(Controller[PydanticSerializer]):
    @validate(_REDIRECT_SPEC)
    async def get(self) -> HttpResponse:
        raise APIRedirectError(
            _REDIRECT_URL,
            status_code=HTTPStatus.FOUND,
        )

    @validate(_REDIRECT_SPEC)
    async def post(self) -> HttpResponseRedirect:
        return HttpResponseRedirect(
            _REDIRECT_URL,
            content_type='application/json',
        )

    @modify(extra_responses=[_REDIRECT_SPEC])
    async def put(self) -> dict[str, str]:
        raise APIRedirectError(
            _REDIRECT_URL,
            status_code=HTTPStatus.FOUND,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
async def test_async_api_redirect(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures we can raise ``APIRedirectError`` in async endpoint."""
    request = dmr_async_rf.generic(str(method), '/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncRedirectController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FOUND, response.content
    assert response.headers == {
        'Content-Type': 'application/json',
        'Location': str(_REDIRECT_URL),
    }
    assert response.content == b''
