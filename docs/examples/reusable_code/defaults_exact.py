from typing_extensions import TypedDict

from dmr.plugins.pydantic import PydanticSerializer
from examples.reusable_code.reusable_defaults import ReusableController


class _RequestModel(TypedDict):
    email: str


class PydanticController(
    ReusableController[PydanticSerializer, _RequestModel],
):
    """Defaults are only used when type args are missing."""


# run: {"controller": "PydanticController", "method": "post", "body": {"email": "example@example.com"}, "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "PydanticController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
