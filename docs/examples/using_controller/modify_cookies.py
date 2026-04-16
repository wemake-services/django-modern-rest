import pydantic

from dmr import Body, Controller, NewCookie, modify
from dmr.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticSerializer]):
    @modify(
        # Add explicit cookie:
        cookies={'user_created': NewCookie(value='true', max_age=1000)},
    )
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        # This response would have an implicit status code `201`
        # and explicit cookie `user_created` set to `true` with `max-age=1000`
        return parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
