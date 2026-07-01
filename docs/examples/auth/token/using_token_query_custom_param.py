from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.token import QueryTokenSyncAuth


# Custom query parameter name (default is `?token=`):
class CustomQueryParamController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (QueryTokenSyncAuth(query_param='api_key'),)

    def get(self) -> str:
        assert self.request.user.username
        return 'authed'


# openapi: {"controller": "CustomQueryParamController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
