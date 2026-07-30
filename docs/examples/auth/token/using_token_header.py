from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import HeaderTokenSyncAuth


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (HeaderTokenSyncAuth(),)

    def get(self) -> str:
        assert self.request.user.is_authenticated
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/users/", "headers": {"X-API-Token": "$X_API_TOKEN"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "APIController", "method": "get", "url": "/api/users/", "headers": {"X-API-Token": "wrong-token"}, "curl_args": ["-D", "-"], "assert-error-text": "401", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
