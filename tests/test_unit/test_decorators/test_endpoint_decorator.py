from http import HTTPStatus
from typing import final

import pytest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse

from django_modern_rest import (
    Controller,
    HeaderSpec,
    ResponseSpec,
    modify,
)
from django_modern_rest.decorators import endpoint_decorator
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _MyController(Controller[PydanticSerializer]):
    @endpoint_decorator(login_required())
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
        return 'Logged in!'

    def put(self) -> str:
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

    response = _MyController.as_view()(request)

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

    response = _MyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content
