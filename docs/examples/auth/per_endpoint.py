from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionSyncAuth


class APIController(Controller[PydanticSerializer]):
    @modify(auth=[DjangoSessionSyncAuth()])
    def get(self) -> str:
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"], "assert-error-text": "Not authenticated", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
