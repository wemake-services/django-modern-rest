from dmr.plugins.pydantic import PydanticFastSerializer
from examples.reusable_code.reusable_defaults import ReusableController


class PydanticController(ReusableController[PydanticFastSerializer]):
    """The request model is not given, so it is `DefaultRequestModel`."""


# run: {"controller": "PydanticController", "method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "PydanticController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
