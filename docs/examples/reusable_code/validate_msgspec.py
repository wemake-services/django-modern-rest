import msgspec
from typing_extensions import override

from dmr.plugins.msgspec import MsgspecSerializer
from examples.reusable_code.validate_reusable import ReusableController


class _RequestModel(msgspec.Struct):
    username: str


class _ResponseBody(msgspec.Struct):
    message: str


class MsgspecController(
    ReusableController[MsgspecSerializer, _RequestModel, _ResponseBody],
):
    @override
    def convert(self, parsed_body: _RequestModel) -> _ResponseBody:
        return _ResponseBody(message=f'Hello, {parsed_body.username}')


# run: {"controller": "MsgspecController", "method": "post", "body": {"username": "sobolevn"}, "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "MsgspecController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
