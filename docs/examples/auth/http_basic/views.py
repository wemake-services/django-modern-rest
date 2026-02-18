from typing import TypedDict

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from examples.auth.http_basic.auth import HttpBasicAsync


class _RequestModel(TypedDict):
    username: str


class UsernameController(
    Body[_RequestModel],
    Controller[PydanticSerializer],
):
    auth = (HttpBasicAsync(),)

    async def post(self) -> str:
        return f'Hello, {self.parsed_body["username"]}'


# run: {"controller": "UsernameController", "method": "post", "body": {"username": "sobolevn"}, "url": "/api/username/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "UsernameController", "method": "post", "body": {"username": "sobolevn"}, "url": "/api/username/", "headers": {"Authorization": "Basic YWRtaW46cGFzcw=="}}  # noqa: ERA001, E501
