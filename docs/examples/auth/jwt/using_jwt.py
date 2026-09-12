from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (HeaderJWTSyncAuth(),)

    def get(self) -> str:
        # Let's test that `User` has the correct type:
        assert self.request.user.is_authenticated
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/users/", "headers": {"Authorization": "Bearer $JWT_ACCESS_TOKEN"}, "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
