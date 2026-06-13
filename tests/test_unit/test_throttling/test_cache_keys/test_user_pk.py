import json
from http import HTTPStatus

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import UserPk


class _SyncController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(1, Rate.second, cache_key=UserPk()),
    ]

    def get(self) -> str:
        return 'inside'


class _NoExclusionsController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(
            1,
            Rate.minute,
            cache_key=UserPk(exclude_superuser=False, exclude_stuff=False),
        ),
    ]

    def get(self) -> str:
        return 'inside'


@pytest.mark.parametrize(
    ('controller_cls', 'user', 'expected_second'),
    [
        (
            _SyncController,
            User(pk=1),
            HTTPStatus.TOO_MANY_REQUESTS,
        ),
        (
            _SyncController,
            User(pk=2, is_superuser=True),
            HTTPStatus.OK,
        ),
        (
            _SyncController,
            User(pk=3, is_staff=True),
            HTTPStatus.OK,
        ),
        (
            _SyncController,
            AnonymousUser(),  # never rate limited
            HTTPStatus.OK,
        ),
        (
            _NoExclusionsController,
            User(pk=4, is_superuser=True),
            HTTPStatus.TOO_MANY_REQUESTS,
        ),
        (
            _NoExclusionsController,
            User(pk=5, is_staff=True),
            HTTPStatus.TOO_MANY_REQUESTS,
        ),
        (
            _NoExclusionsController,
            AnonymousUser(),
            HTTPStatus.OK,
        ),
    ],
)
def test_sync_throttle_user_pk_cases(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    controller_cls: type[Controller[PydanticSerializer]],
    user: User,
    expected_second: HTTPStatus,
) -> None:
    """Ensures `UserPk` throttling behavior for all user categories."""
    request = dmr_rf.get('/whatever/')
    request.user = user
    response = controller_cls.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == 'inside'

    request = dmr_rf.get('/whatever/')
    request.user = user
    response = controller_cls.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_second
