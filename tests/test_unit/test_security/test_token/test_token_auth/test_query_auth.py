from http import HTTPStatus
from typing import final

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import QueryTokenAsyncAuth, QueryTokenSyncAuth
from dmr.security.token.logic import token_acreate, token_create
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@pytest.mark.django_db
def test_query_token_sync_auth_success(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures QueryTokenSyncAuth reads the token from the query string."""

    @final
    class _QueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenSyncAuth(),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = token_create(
        user=admin_user,
        name='query-test',
    )
    request = dmr_rf.get('/whatever/', data={'token': raw_token})

    response = _QueryController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_query_token_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures QueryTokenAsyncAuth reads the token from the query string."""

    @final
    class _AsyncQueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenAsyncAuth(),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await token_acreate(
        user=admin_user,
        name='async-query-test',
    )
    request = dmr_async_rf.get('/whatever/', data={'token': raw_token})

    response = await dmr_async_rf.wrap(_AsyncQueryController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
