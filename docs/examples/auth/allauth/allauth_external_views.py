import json
from typing import Final

from allauth.headless.account.views import LoginView, SessionView
from allauth.headless.constants import Client

from dmr import Controller
from dmr.openapi import load_schema
from dmr.openapi.objects import PathItem
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, external_path, path
from dmr.security.allauth import XSessionTokenSyncAuth

# `django-allauth` serves these two endpoints, we only describe them.
# Its own OpenAPI specification has the full definitions:
# https://docs.allauth.org/en/latest/headless/openapi-specification/
_LOGIN_OPENAPI: Final = """
{
  "post": {
    "operationId": "login",
    "summary": "Log in and receive a session token",
    "responses": {
      "200": {"description": "The session token is in the body"},
      "400": {"description": "Missing fields or wrong credentials"}
    }
  }
}
"""

_SESSION_OPENAPI: Final = """
{
  "get": {
    "operationId": "currentSession",
    "summary": "Inspect the session behind the token",
    "responses": {
      "200": {"description": "The session is valid"},
      "401": {"description": "No or unknown session token"}
    }
  },
  "delete": {
    "operationId": "logout",
    "summary": "Log out and invalidate the session token",
    "responses": {
      "401": {"description": "Logged out, the token no longer resolves"}
    }
  }
}
"""


class MeController(Controller[PydanticSerializer]):
    """Our own endpoint, protected by the token `allauth` issued."""

    auth = (XSessionTokenSyncAuth(),)

    def get(self) -> str:
        assert self.request.user.is_authenticated
        return 'authed'


router = Router(
    'auth/',
    urls=[
        external_path(
            'login/',
            LoginView.as_api_view(client=Client.APP),
            name='login',
            openapi=load_schema(json.loads(_LOGIN_OPENAPI), PathItem),
        ),
        external_path(
            'session/',
            SessionView.as_api_view(client=Client.APP),
            name='current_session',
            openapi=load_schema(json.loads(_SESSION_OPENAPI), PathItem),
        ),
        path('me/', MeController.as_view(), name='me'),
    ],
)
