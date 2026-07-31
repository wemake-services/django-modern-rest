from http import HTTPStatus
from typing import final

import pytest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse

from dmr import Controller, HeaderSpec, ResponseSpec, modify
from dmr.decorators import endpoint_decorator
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _SyncController(Controller[PydanticSerializer]):
    @endpoint_decorator(login_required(login_url='./test/login/'))
    @modify(
        validate_responses=False,  # we need this, because of the content-type
        extra_responses=[
            ResponseSpec(
                None,
                status_code=HTTPStatus.FOUND,
                headers={'Location': HeaderSpec()},
            ),
        ],
    )
    def get(self) -> str:
        assert isinstance(self, _SyncController), self
        return 'Logged in!'

    def put(self) -> str:
        assert isinstance(self, _SyncController), self
        return 'No login'


@pytest.mark.parametrize(
    ('user', 'status_code'),
    [
        (AnonymousUser(), HTTPStatus.FOUND),
        (User(), HTTPStatus.OK),
    ],
)
def test_login_required_get(
    dmr_rf: DMRRequestFactory,
    *,
    user: User | AnonymousUser,
    status_code: HTTPStatus,
) -> None:
    """Ensures that ``get`` works and authed user is required."""
    request = dmr_rf.get('/whatever/')
    request.user = user

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


@pytest.mark.parametrize(
    ('user', 'status_code'),
    [
        (AnonymousUser(), HTTPStatus.OK),
        (User(), HTTPStatus.OK),
    ],
)
def test_login_not_required_put(
    dmr_rf: DMRRequestFactory,
    *,
    user: User | AnonymousUser,
    status_code: HTTPStatus,
) -> None:
    """Ensures that ``put`` works and authed user is not required."""
    request = dmr_rf.put('/whatever/')
    request.user = user

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


@final
class _AsyncController(Controller[PydanticSerializer]):
    @endpoint_decorator(login_required(login_url='./test/login/'))
    @modify(
        validate_responses=False,  # we need this, because of the content-type
        extra_responses=[
            ResponseSpec(
                None,
                status_code=HTTPStatus.FOUND,
                headers={'Location': HeaderSpec()},
            ),
        ],
    )
    async def get(self) -> str:
        assert isinstance(self, _AsyncController), self
        return 'Logged in!'

    async def put(self) -> str:
        assert isinstance(self, _AsyncController), self
        return 'No login'


async def _resolve(user: User | AnonymousUser) -> User | AnonymousUser:
    return user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('user', 'status_code'),
    [
        (AnonymousUser(), HTTPStatus.FOUND),
        (User(), HTTPStatus.OK),
    ],
)
async def test_async_login_required_get(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    user: User | AnonymousUser,
    status_code: HTTPStatus,
) -> None:
    """Ensures that ``get`` works and authed user is required."""
    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(user)

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


@pytest.mark.parametrize(
    ('user', 'status_code'),
    [
        (AnonymousUser(), HTTPStatus.OK),
        (User(), HTTPStatus.OK),
    ],
)
async def test_async_login_not_required_put(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    user: User | AnonymousUser,
    status_code: HTTPStatus,
) -> None:
    """Ensures that ``put`` works and authed user is not required."""
    request = dmr_async_rf.put('/whatever/')
    request.auser = lambda: _resolve(user)

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content
