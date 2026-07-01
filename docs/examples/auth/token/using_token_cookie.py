from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import CookieTokenSyncAuth


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (CookieTokenSyncAuth(),)

    def get(self) -> str:
        # Let's test that `User` is authenticated:
        assert self.request.user.is_authenticated
        return 'authed'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
