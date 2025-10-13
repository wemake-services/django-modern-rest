from http import HTTPStatus
from typing import final

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser, User

from django_modern_rest import Controller, dispatch_decorator
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
@dispatch_decorator(login_required())
class _MyController(Controller[PydanticSerializer]):
    def get(self) -> str:
        """Simulates `post` method."""
        return 'Logged in!'


def test_anonymous_user(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `."""
    request = dmr_rf.get('/whatever/')
    request.user = AnonymousUser()

    response = _MyController.as_view()(request)

    assert response.status_code == HTTPStatus.FOUND


def test_regular_user(dmr_rf: DMRRequestFactory) -> None:
    """Ensures `."""
    request = dmr_rf.get('/whatever/')
    request.user = User()

    response = _MyController.as_view()(request)

    assert response.status_code == HTTPStatus.OK
