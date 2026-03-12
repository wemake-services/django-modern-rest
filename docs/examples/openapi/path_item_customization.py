import msgspec

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class QueryModel(msgspec.Struct):
    search: str
    max_items: int


class UserController(Controller[MsgspecSerializer]):
    description = 'Find '

    def post(self) -> str:
        return 'post'
