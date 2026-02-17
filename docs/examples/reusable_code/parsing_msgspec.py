from typing_extensions import TypedDict, override

from dmr.plugins.msgspec import MsgspecSerializer
from examples.reusable_code.reusable_parsing import ReusableController


class _RequestModel(TypedDict):
    username: str


class _ResponseBody(TypedDict):
    message: str


class MsgspecController(
    ReusableController[MsgspecSerializer, _RequestModel, _ResponseBody],
):
    @override
    def convert(self, parsed_body: _RequestModel) -> _ResponseBody:
        return {'message': f'Hello, {parsed_body["username"]}'}


# run: {"controller": "MsgspecController", "method": "post", "body": {"username": "sobolevn"}, "url": "/api/example/"}  # noqa: ERA001, E501
