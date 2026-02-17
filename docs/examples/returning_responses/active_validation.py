from http import HTTPStatus

import msgspec

from dmr import APIError, Body, Controller, Headers
from dmr.errors import ErrorType
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class HeaderModel(msgspec.Struct):
    consumer: str = msgspec.field(name='X-API-Consumer')


class UserController(
    Controller[MsgspecSerializer],
    Body[UserModel],
    Headers[HeaderModel],
):
    def post(self) -> UserModel:
        if self.parsed_headers.consumer != 'my-api':
            # Notice that this response is never documented in the spec,
            # so, it will raise an error when validation is enabled (default).
            raise APIError(
                self.format_error(
                    'Wrong API consumer',
                    error_type=ErrorType.user_msg,
                ),
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            )
        # This response will be documented by default:
        return self.parsed_body


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "headers": {"X-API-Consumer": "my-api"}, "url": "/api/user/"}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "headers": {"X-API-Consumer": "not-my-api"}, "url": "/api/user/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
