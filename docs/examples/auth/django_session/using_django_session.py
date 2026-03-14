from typing import assert_type

from django.contrib.auth.models import User
from django.http import HttpRequest

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth


class AuthenticatedHttpRequest(HttpRequest):
    user: User


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest

    @modify(auth=[DjangoSessionSyncAuth()])
    def get(self) -> str:
        # Let's test that `User` has the correct type:
        assert_type(self.request.user, User)
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
