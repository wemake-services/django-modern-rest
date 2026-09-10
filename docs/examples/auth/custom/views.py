from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from examples.auth.custom.auth import ProxyHeaderSyncAuth


class ProfileController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (ProxyHeaderSyncAuth(),)

    def get(self) -> str:
        username = self.request.user.username
        return f'Hello, {username}'


# run: {"controller": "ProfileController", "method": "get", "url": "/api/profile/", "headers": {"X-Forwarded-User": "test_user"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "ProfileController", "method": "get", "url": "/api/profile/", "curl_args": ["-D", "-"], "assert-error-text": "Not authenticated", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ProfileController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
