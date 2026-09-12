from dmr import Controller, modify
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    tags = ('users',)  # All endpoints are tagged as 'users'

    def get(self) -> str:
        return 'get'

    @modify(tags=['admin'])  # This one is tagged as 'users' and 'admin'
    def post(self) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
