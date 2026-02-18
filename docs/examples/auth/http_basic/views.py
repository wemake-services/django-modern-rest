from typing import TypedDict

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from examples.auth.http_basic.auth import HttpBasicAsync


class _RequestModel(TypedDict):
    bill: str


class BillController(
    Body[_RequestModel],
    Controller[PydanticSerializer],
):
    auth = (HttpBasicAsync(),)

    async def post(self) -> str:
        return f'Processing bill: {self.parsed_body["bill"]}'


# run: {"controller": "BillController", "method": "post", "body": {"bill": "parking"}, "url": "/api/username/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "BillController", "method": "post", "body": {"bill": "parking"}, "url": "/api/username/", "headers": {"Authorization": "Basic YWRtaW46cGFzcw=="}}  # noqa: ERA001, E501
