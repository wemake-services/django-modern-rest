from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import HeaderTokenSyncAuth, request_token


class RevokeTokenController(Controller[PydanticSerializer]):
    """Revoke the token used to make this request."""

    request: AuthenticatedHttpRequest[User]
    auth = (HeaderTokenSyncAuth(),)

    def delete(self) -> None:
        request_token(self.request, strict=True).revoke()


# openapi: {"controller": "RevokeTokenController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
