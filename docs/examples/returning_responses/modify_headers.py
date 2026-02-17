from http import HTTPStatus

import pydantic

from dmr import Body, Controller, NewHeader, modify
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


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
