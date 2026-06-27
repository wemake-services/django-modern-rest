from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import HeaderTokenSyncAuth


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (HeaderTokenSyncAuth(),)

    def get(self) -> str:
        # Let's test that `User` has the correct type:
        assert self.request.user.username
        return 'authed'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
