from typing import final

from typing_extensions import TypedDict, override

from django_modern_rest.plugins.msgspec import MsgspecSerializer
from examples.reusable_code.reusable_parsing import ReusableController


@final
class _RequestModel(TypedDict):
    username: str


@final
class _ResponseBody(TypedDict):
    message: str


@final
class MsgspecController(
    ReusableController[MsgspecSerializer, _RequestModel, _ResponseBody],
):
    @override
    def convert(self, parsed_body: _RequestModel) -> _ResponseBody:
        return {'message': f'Hello, {parsed_body["username"]}'}


# run: {"controller": "MsgspecController", "method": "post", "body": {"username": "sobolevn"}, "url": "/api/example/"}  # noqa: ERA001, E501
