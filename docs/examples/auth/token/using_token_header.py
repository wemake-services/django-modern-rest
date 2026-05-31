from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import TokenSyncAuth


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (TokenSyncAuth(),)

    def get(self) -> str:
        # Let's test that `User` has the correct type:
        assert self.request.user.username
        return 'authed'


# Custom header name (default is `X-API-Token`):
class CustomHeaderController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (TokenSyncAuth(header_name='Authorization', prefix='Token'),)

    def get(self) -> str:
        assert self.request.user.username
        return 'authed'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
