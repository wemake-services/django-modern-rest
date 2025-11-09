from http import HTTPStatus
from typing import final

import pydantic

from django_modern_rest import Body, Controller, NewHeader, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


@final
class UserController(
    Controller[PydanticSerializer],
    Body[UserModel],
):
    @modify(
        status_code=HTTPStatus.OK,
        # Add explicit header:
        headers={'X-Created': NewHeader(value='true')},
    )
    def post(self) -> UserModel:
        # This response would have an explicit status code `200`
        # and new explicit header `{'X-Created': 'true'}`:
        return self.parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
