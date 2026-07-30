from http import HTTPStatus

from django.contrib.auth.models import User

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import HeaderTokenSyncAuth, request_token


class RevokeTokenController(Controller[PydanticSerializer]):
    """Revoke the token used to make this request."""

    request: AuthenticatedHttpRequest[User]
    auth = (HeaderTokenSyncAuth(),)

    @modify(status_code=HTTPStatus.NO_CONTENT)
    def delete(self) -> None:
        token = request_token(self.request, strict=True)
        token.revoke()


# openapi: {"controller": "RevokeTokenController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
