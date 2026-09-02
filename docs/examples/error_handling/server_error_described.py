from http import HTTPStatus

import msgspec

from dmr import Body, Controller, ResponseSpec
from dmr.errors import ErrorModel
from dmr.exceptions import InternalServerError
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    # Now `500` is a part of our public contract:
    # it is in the OpenAPI schema and its body is validated.
    responses = (
        ResponseSpec(ErrorModel, status_code=HTTPStatus.INTERNAL_SERVER_ERROR),
    )

    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        if parsed_body.email.endswith('@example.com'):
            # Imagine that our storage is down for this user:
            raise InternalServerError('Cannot reach the database')
        # This response will be documented by default:
        return parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "post", "body": {"email": "user@example.com"}, "url": "/api/user/", "curl_args": ["-D", "-"], "assert-error-text": "Internal server error", "fail-with-body": false}  # noqa: ERA001, E501
