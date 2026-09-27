from dmr.plugins.pydantic import PydanticFastSerializer
from examples.reusable_code.reusable_controller import ReusableController


class PydanticController(ReusableController[PydanticFastSerializer]):
    """This controller will use pydantic for serialization."""


# run: {"controller": "PydanticController", "method": "get", "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "PydanticController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
