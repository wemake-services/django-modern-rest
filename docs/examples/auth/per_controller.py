from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWTAsyncAuth


class APIController(Controller[PydanticSerializer]):
    auth = (JWTAsyncAuth(),)

    async def get(self) -> str:
        return 'authed'


# run: {"controller": "APIController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
