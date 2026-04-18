from typing import TypedDict

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from examples.auth.http_basic.auth import HttpBasicAsync


class _RequestModel(TypedDict):
    bill: str


class BillController(Controller[PydanticSerializer]):
    auth = (HttpBasicAsync(),)

    async def post(self, parsed_body: Body[_RequestModel]) -> str:
        return f'Processing bill: {parsed_body["bill"]}'


# run: {"controller": "BillController", "method": "post", "body": {"bill": "parking"}, "url": "/api/username/", "curl_args": ["-D", "-"], "assert-error-text": "Not authenticated", "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "BillController", "method": "post", "body": {"bill": "parking"}, "url": "/api/username/", "headers": {"Authorization": "Basic YWRtaW46cGFzcw=="}}  # noqa: ERA001, E501
# openapi: {"controller": "BillController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
