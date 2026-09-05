from http import HTTPStatus

import msgspec

from dmr import Body, Controller
from dmr.exceptions import InternalServerError
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    # We still validate everything else, but `500` is not in our schema:
    exclude_validate_responses = frozenset((HTTPStatus.INTERNAL_SERVER_ERROR,))

    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        if parsed_body.email.endswith('@example.com'):
            # Imagine that our storage is down for this user.
            # This response is never documented in the spec, but it won't be
            # replaced with a `422`, because `500` is excluded above.
            raise InternalServerError('Cannot reach the database')
        # This response will be documented by default:
        return parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "post", "body": {"email": "user@example.com"}, "url": "/api/user/", "curl_args": ["-D", "-"], "assert-error-text": "Internal server error", "fail-with-body": false}  # noqa: ERA001, E501
