from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.security.token.logic import token_create


class IssueTokenController(Controller[PydanticSerializer]):
    """Issue a new API token for the currently authenticated user."""

    request: AuthenticatedHttpRequest[User]
    auth = (DjangoSessionSyncAuth(),)

    def post(self) -> None:
        token, raw_token = token_create(  # noqa: RUF059
            user=self.request.user,
            name='api-key',
        )
        # raw_token is only available here - return it to the client now.
        # Only its hash is stored; it cannot be recovered after this point.
        # In production, include token.pk, token.name, token.expires_at,
        # and raw_token in a typed response model.


# openapi: {"controller": "IssueTokenController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
