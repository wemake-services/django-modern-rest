from dmr import Controller
from dmr.openapi.objects import Server
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    description = 'Create new users'
    servers = (
        Server(url='https://example.com'),
        Server(url='https://dev.example.com'),
    )

    def post(self) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
