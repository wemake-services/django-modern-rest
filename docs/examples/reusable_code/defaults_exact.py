from typing_extensions import TypedDict

from dmr.plugins.pydantic import PydanticSerializer
from examples.reusable_code.reusable_defaults import ReusableController


class _RequestModel(TypedDict):
    email: str


class PydanticController(
    ReusableController[PydanticSerializer, _RequestModel],
):
    """
    Defaults are only used when type args are missing.

    ``DefaultRequestModel`` is fully replaced here,
    so its payload does not validate anymore.
    """


# run: {"controller": "PydanticController", "method": "post", "body": {"email": "example@example.com"}, "url": "/api/example/"}  # noqa: ERA001, E501
# run: {"controller": "PydanticController", "method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/", "curl_args": ["-D", "-"], "assert-error-text": "\"email\"", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "PydanticController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
