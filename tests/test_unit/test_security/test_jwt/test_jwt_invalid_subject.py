import datetime as dt
from http import HTTPStatus
from typing import Final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import JWTAsyncAuth, JWToken, JWTSyncAuth
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


def _encode(subject: str, secret: str) -> str:
    return JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=subject,
    ).encode(secret=secret, algorithm='HS256')


class _SyncController(Controller[PydanticFastSerializer]):
    auth = (JWTSyncAuth(),)

    def get(self) -> str:
        raise NotImplementedError


class _AsyncController(Controller[PydanticFastSerializer]):
    auth = (JWTAsyncAuth(),)

    async def get(self) -> str:
        raise NotImplementedError


# The default `user_id_field` is `pk`, which is an integer column.
# A signed token can still carry anything at all in `sub`.
# An empty `sub` is not listed: `JWToken` rejects it on both
# encode and decode, so it never reaches the user lookup.
_INVALID_SUBJECTS: Final = ('admin', 'not-a-number', '1.5', '{}', 'null')


@pytest.mark.django_db
@pytest.mark.parametrize('subject', _INVALID_SUBJECTS)
def test_sync_jwt_non_numeric_subject(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
    *,
    subject: str,
) -> None:
    """Ensures a subject that cannot be a `pk` is a 401, not a 500."""
    token = _encode(subject, settings.SECRET_KEY)
    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': f'Bearer {token}'},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('subject', _INVALID_SUBJECTS)
async def test_async_jwt_non_numeric_subject(
    dmr_async_rf: DMRAsyncRequestFactory,
    settings: LazySettings,
    *,
    subject: str,
) -> None:
    """Ensures a subject that cannot be a `pk` is a 401, not a 500."""
    token = _encode(subject, settings.SECRET_KEY)
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Authorization': f'Bearer {token}'},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
def test_sync_jwt_subject_validation_error(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures `ValidationError` from a field is a 401, not a 500."""

    class _ValidatingController(Controller[PydanticFastSerializer]):
        # `date_joined` validates on conversion and raises
        # `ValidationError` instead of `ValueError`, same as `UUIDField`:
        auth = (JWTSyncAuth(user_id_field='date_joined'),)

        def get(self) -> str:
            raise NotImplementedError

    token = _encode('definitely-not-a-date', settings.SECRET_KEY)
    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': f'Bearer {token}'},
    )

    response = _ValidatingController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
def test_sync_jwt_valid_subject_still_works(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures the widened `except` did not swallow successful auth."""

    class _OkController(Controller[PydanticFastSerializer]):
        auth = (JWTSyncAuth(),)

        def get(self) -> str:
            assert self.request.user.pk == admin_user.pk
            return 'authed'

    token = _encode(str(admin_user.pk), settings.SECRET_KEY)
    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': f'Bearer {token}'},
    )

    response = _OkController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
