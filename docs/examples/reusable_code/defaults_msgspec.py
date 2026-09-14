from typing_extensions import TypedDict

from dmr.plugins.msgspec import MsgspecSerializer
from examples.reusable_code.reusable_defaults import ReusableController


class _RequestModel(TypedDict):
    email: str


class MsgspecController(
    ReusableController[MsgspecSerializer, _RequestModel],
):
    """Defaults are only used when type args are missing."""


# run: {"controller": "MsgspecController", "method": "post", "body": {"email": "example@example.com"}, "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "MsgspecController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
