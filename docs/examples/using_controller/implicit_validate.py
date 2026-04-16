from http import HTTPStatus

import pydantic
from django.http import HttpResponse

from dmr import Body, Controller, ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticSerializer]):
    responses = (
        # Describes unique return types for this controller:
        ResponseSpec(UserModel, status_code=HTTPStatus.OK),
    )

    def post(self, parsed_body: Body[UserModel]) -> HttpResponse:
        # This response would have an explicit status code `200`:
        return self.to_response(
            parsed_body,
            status_code=HTTPStatus.OK,
        )

    def put(self, parsed_body: Body[UserModel]) -> HttpResponse:
        return self.to_response(
            parsed_body,
            status_code=HTTPStatus.OK,
        )


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "put", "body": {"email": "user@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
