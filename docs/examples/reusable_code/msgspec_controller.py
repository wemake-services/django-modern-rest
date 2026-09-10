from dmr.plugins.msgspec import MsgspecSerializer
from examples.reusable_code.reusable_controller import ReusableController


class MsgspecController(ReusableController[MsgspecSerializer]):
    """This controller will use msgspec for serialization."""


# run: {"controller": "MsgspecController", "method": "get", "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "MsgspecController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
