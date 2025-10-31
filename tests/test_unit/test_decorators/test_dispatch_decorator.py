from http import HTTPStatus
from typing import final

import pytest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User

from django_modern_rest import Controller
from django_modern_rest.decorators import dispatch_decorator
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
@dispatch_decorator(login_required())
class _MyController(Controller[PydanticSerializer]):
    def get(self) -> str:
        """Simulates `post` method."""
        return 'Logged in!'


@pytest.mark.parametrize(
    ('user', 'status_code'),
    [
        (AnonymousUser(), HTTPStatus.FOUND),
        (User(), HTTPStatus.OK),
    ],
)
def test_login_required(
    dmr_rf: DMRRequestFactory,
    *,
    user: User | AnonymousUser,
    status_code: HTTPStatus,
) -> None:
    """Ensures that ``dispatch_decorator`` works and authed user is required."""
    request = dmr_rf.get('/whatever/')
    request.user = user

    response = _MyController.as_view()(request)

    assert response.status_code == status_code
