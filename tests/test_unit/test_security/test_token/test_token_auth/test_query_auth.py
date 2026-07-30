from http import HTTPStatus
from typing import Final

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import QueryTokenAsyncAuth, QueryTokenSyncAuth
from dmr.security.token.app.models import Token
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_CORRECT_TEMPLATE: Final = '{0}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('query_param', 'query_value', 'expected_status'),
    [
        ('token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('token', 'Prefix {0}', HTTPStatus.UNAUTHORIZED),
        ('wrong', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('token', _CORRECT_TEMPLATE, HTTPStatus.OK),
    ],
)
def test_query_token_sync_auth(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    *,
    query_param: str,
    query_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures QueryTokenSyncAuth reads the token from the query string."""

    class _QueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenSyncAuth(),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='query-test',
    )
    request = dmr_rf.get(
        '/whatever/',
        data={query_param: query_value.format(raw_token)},
    )

    response = _QueryController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    'query_param',
    [
        'token',
        'custom',
    ],
)
def test_query_token_sync_auth_custom_query_param(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    *,
    query_param: str,
) -> None:
    """Ensures QueryTokenSyncAuth reads the token from the query string."""

    class _QueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenSyncAuth(query_param=query_param),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='query-test',
    )

    request = dmr_rf.get('/whatever/', data={query_param: raw_token})
    response = _QueryController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    request = dmr_rf.get('/whatever/', data={'wrong_param': raw_token})
    response = _QueryController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('query_param', 'query_value', 'expected_status'),
    [
        ('token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('token', 'Prefix {0}', HTTPStatus.UNAUTHORIZED),
        ('wrong', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('token', _CORRECT_TEMPLATE, HTTPStatus.OK),
    ],
)
async def test_async_query_token_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    query_param: str,
    query_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures QueryTokenAsyncAuth reads the token from the query string."""

    class _AsyncQueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenAsyncAuth(),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-query-test',
    )
    request = dmr_async_rf.get(
        '/whatever/',
        data={query_param: query_value.format(raw_token)},
    )

    response = await dmr_async_rf.wrap(_AsyncQueryController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    'query_param',
    [
        'token',
        'custom',
    ],
)
async def test_async_query_token_custom_query_param(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    query_param: str,
) -> None:
    """Ensures QueryTokenAsyncAuth reads the token from the query string."""

    class _AsyncQueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenAsyncAuth(query_param=query_param),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-query-test',
    )

    request = dmr_async_rf.get('/whatever/', data={query_param: raw_token})
    response = await dmr_async_rf.wrap(_AsyncQueryController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    request = dmr_async_rf.get('/whatever/', data={'wrong': raw_token})
    response = await dmr_async_rf.wrap(_AsyncQueryController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
