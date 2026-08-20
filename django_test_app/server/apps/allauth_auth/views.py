from typing import Final, final

import pydantic

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.allauth import (
    XSessionTokenAsyncAuth,
    XSessionTokenSyncAuth,
    request_allauth_session,
)

# `django-allauth` serves these two endpoints itself, we only describe them.
# Both are part of its headless `app` client API.
# See https://docs.allauth.org/en/latest/headless/openapi-specification/

LOGIN_OPENAPI: Final = """
{
  "post": {
    "operationId": "allauthAuth_login",
    "summary": "Log in and receive a session token",
    "requestBody": {
      "required": true,
      "content": {
        "application/json": {
          "schema": {
            "type": "object",
            "properties": {
              "username": {
                "type": "string"
              },
              "password": {
                "type": "string"
              }
            },
            "required": [
              "username",
              "password"
            ]
          }
        }
      }
    },
    "responses": {
      "200": {
        "description": "Logged in, the session token is in the body",
        "content": {
          "application/json": {
            "schema": {
              "type": "object",
              "properties": {
                "meta": {
                  "type": "object",
                  "properties": {
                    "session_token": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "session_token"
                  ]
                }
              },
              "required": [
                "meta"
              ]
            }
          }
        }
      },
      "400": {
        "description": "Missing fields or wrong credentials"
      },
      "401": {
        "description": "Login needs another step, such as MFA"
      },
      "409": {
        "description": "Already logged in"
      }
    }
  }
}
"""

SESSION_OPENAPI: Final = """
{
  "get": {
    "operationId": "allauthAuth_currentSession",
    "summary": "Inspect the session behind the token",
    "responses": {
      "200": {
        "description": "The session is valid"
      },
      "401": {
        "description": "No or unknown session token"
      }
    }
  },
  "delete": {
    "operationId": "allauthAuth_logout",
    "summary": "Log out and invalidate the session token",
    "responses": {
      "401": {
        "description": "Logged out, the token no longer resolves"
      }
    }
  }
}
"""


@final
class _SessionUserOutput(pydantic.BaseModel):
    username: str
    email: str
    is_active: bool


@final
class ControllerWithSessionTokenSyncAuth(Controller[PydanticSerializer]):
    """Sync endpoint protected by an `allauth` session token."""

    auth = (XSessionTokenSyncAuth(),)

    def get(self) -> _SessionUserOutput:
        """Return the user that the session token resolved into."""
        assert request_allauth_session(self.request, strict=True)  # noqa: S101
        return _SessionUserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithSessionTokenAsyncAuth(Controller[PydanticSerializer]):
    """Async endpoint protected by an `allauth` session token."""

    auth = (XSessionTokenAsyncAuth(),)

    async def get(self) -> _SessionUserOutput:
        """Return the user that the session token resolved into."""
        assert request_allauth_session(self.request, strict=True)  # noqa: S101
        return _SessionUserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )
