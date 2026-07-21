from http import HTTPStatus

import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserSignup(pydantic.BaseModel):
    age: int


class SignupController(Controller[PydanticSerializer]):
    # Return `422 Unprocessable Entity` instead of the default `400`
    # when the incoming request fails validation:
    request_validation_error_status = HTTPStatus.UNPROCESSABLE_ENTITY

    def post(self, parsed_body: Body[UserSignup]) -> int:
        return parsed_body.age
