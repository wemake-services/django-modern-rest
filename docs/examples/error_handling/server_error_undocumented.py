import msgspec

from dmr import Body, Controller
from dmr.exceptions import InternalServerError
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class UserController(Controller[MsgspecSerializer]):
    # `500` is not documented here, we treat it as a bug and not as a feature.
    # In development an undocumented `500` is reported as a `422`
    # with `Returned status code 500 is not specified` message,
    # which is a hint that something is wrong with this endpoint.
    def post(self, parsed_body: Body[UserModel]) -> UserModel:
        if parsed_body.email.endswith('@example.com'):
            # Imagine that our storage is down for this user:
            raise InternalServerError('Cannot reach the database')
        # This response will be documented by default:
        return parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
