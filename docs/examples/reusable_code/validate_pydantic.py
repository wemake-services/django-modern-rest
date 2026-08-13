import pydantic
from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from examples.reusable_code.validate_reusable import ReusableController


class _RequestModel(pydantic.BaseModel):
    first_name: str
    last_name: str


class _ResponseBody(pydantic.BaseModel):
    full_name: str


class PydanticController(
    ReusableController[PydanticSerializer, _RequestModel, _ResponseBody],
):
    @override
    def convert(self, parsed_body: _RequestModel) -> _ResponseBody:
        return _ResponseBody(
            full_name=(f'{parsed_body.first_name} {parsed_body.last_name}'),
        )


# run: {"controller": "PydanticController", "method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "PydanticController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
