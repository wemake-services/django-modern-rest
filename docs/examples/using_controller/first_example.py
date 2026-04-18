from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


class MyController(Controller[MsgspecSerializer]):
    def post(self) -> str:
        return 'ok'


# run: {"controller": "MyController", "method": "post", "url": "/api/example/"}  # noqa: ERA001
# openapi: {"controller": "MyController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
