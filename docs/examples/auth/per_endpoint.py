from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import (
    DjangoSessionSyncAuth,
)


class APIController(Controller[PydanticSerializer]):
    @modify(auth=[DjangoSessionSyncAuth()])
    def get(self) -> str:
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
