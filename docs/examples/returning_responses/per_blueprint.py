from http import HTTPStatus

import msgspec

from dmr import APIError, Blueprint, Body, Headers
from dmr.errors import ErrorType
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class HeaderModel(msgspec.Struct):
    consumer: str = msgspec.field(name='X-API-Consumer')


class UserBlueprint(
    Blueprint[MsgspecSerializer],
    Body[UserModel],
    Headers[HeaderModel],
):
    # Now, we won't validate all endpoints in this blueprint:
    validate_responses = False

    def post(self) -> UserModel:
        if self.parsed_headers.consumer != 'my-api':
            # Notice that this response is never documented in the spec,
            # but, it won't raise a validation error, because validation is off
            raise APIError(
                self.format_error(
                    'Wrong API consumer',
                    error_type=ErrorType.user_msg,
                ),
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            )
        # This response will be documented by default:
        return self.parsed_body
