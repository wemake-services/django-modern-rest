import datetime as dt

from django.contrib.auth.models import User
from pydantic import BaseModel

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import HeaderTokenSyncAuth
from dmr.security.token.models import Token


class TokenOut(BaseModel):
    id: int
    name: str
    expires_at: dt.datetime | None
    raw_token: str


class IssueTokenController(Controller[PydanticSerializer]):
    """Issue a new token for the authenticated user."""

    request: AuthenticatedHttpRequest[User]
    auth = (HeaderTokenSyncAuth(),)

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


# openapi: {"controller": "IssueTokenController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
