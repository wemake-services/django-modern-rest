from http import HTTPStatus

import pydantic

from dmr import Body, Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.OK)
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an explicit status code `200`:
        return parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
