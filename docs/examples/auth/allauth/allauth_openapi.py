"""
OpenAPI descriptions of the two ``django-allauth`` headless endpoints.

They live here so the routing example stays about routing.
These are trimmed down to what the example needs, the full definitions
are in ``django-allauth``'s own specification:
https://docs.allauth.org/en/latest/headless/openapi-specification/
"""

import json
from typing import Final

from dmr.openapi import load_schema
from dmr.openapi.objects import PathItem

_LOGIN_SCHEMA: Final = """
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

_SESSION_SCHEMA: Final = """
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

#: Describes ``allauth``'s login endpoint.
LOGIN_PATH_ITEM: Final = load_schema(json.loads(_LOGIN_SCHEMA), PathItem)

#: Describes ``allauth``'s current session endpoint.
SESSION_PATH_ITEM: Final = load_schema(json.loads(_SESSION_SCHEMA), PathItem)
