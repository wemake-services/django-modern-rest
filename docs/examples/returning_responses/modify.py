from http import HTTPStatus

import pydantic

from django_modern_rest import Body, Controller, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(
    Controller[PydanticSerializer],
    Body[UserModel],
):
    @modify(status_code=HTTPStatus.OK)
    def post(self) -> UserModel:
        # This response would have an explicit status code `200`:
        return self.parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
