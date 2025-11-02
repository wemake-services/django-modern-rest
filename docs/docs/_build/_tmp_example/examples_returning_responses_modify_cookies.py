from typing import final

import pydantic

from django_modern_rest import Body, Controller, NewCookie, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


@final
class UserController(
    Controller[PydanticSerializer],
    Body[UserModel],
):
    @modify(
        # Add explicit cookie:
        cookies={'user_created': NewCookie(value='true', max_age=1000)},
    )
    def post(self) -> UserModel:
        # This response would have an implicit status code `201`
        # and explicit cookie `user_created` set to `true` with `max-age=1000`
        return self.parsed_body

