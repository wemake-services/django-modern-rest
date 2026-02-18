from http import HTTPStatus

import pydantic
from django.http import HttpResponse

from dmr import (
    Body,
    Controller,
    ResponseSpec,
    validate,
)
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(
    Controller[PydanticSerializer],
    Body[UserModel],
):
    @validate(  # <- describes unique return types from this endpoint
        ResponseSpec(
            UserModel,
            status_code=HTTPStatus.OK,
        ),
    )
    def post(self) -> HttpResponse:
        # This response would have an explicit status code `200`:
        return self.to_response(
            self.parsed_body,
            status_code=HTTPStatus.OK,
        )


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
