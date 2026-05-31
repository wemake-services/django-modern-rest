import datetime as dt

from django.contrib.auth.models import User
from pydantic import BaseModel

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import TokenSyncAuth, request_token
from dmr.security.token.models import Token


class TokenOut(BaseModel):
    id: int
    name: str
    expires_at: dt.datetime | None
    raw_token: str


class IssueTokenController(Controller[PydanticSerializer]):
    """Issue a new token for the authenticated user."""

    request: AuthenticatedHttpRequest[User]
    auth = (TokenSyncAuth(),)

    def post(self) -> TokenOut:
        token, raw_token = Token.objects.create_token(
            user=self.request.user,
            name='api-key',
        )
        return TokenOut(
            id=token.pk,
            name=token.name,
            expires_at=token.expires_at,
            raw_token=raw_token,
        )


class RevokeTokenController(Controller[PydanticSerializer]):
    """Revoke the token used to make this request."""

    request: AuthenticatedHttpRequest[User]
    auth = (TokenSyncAuth(),)

    def delete(self) -> None:
        request_token(self.request, strict=True).revoke()


# openapi: {"controller": "IssueTokenController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
