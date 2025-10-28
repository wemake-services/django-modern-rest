from http import HTTPStatus
from typing import final

import msgspec

from django_modern_rest import APIError, Body, Controller, Headers, modify
from django_modern_rest.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class HeaderModel(msgspec.Struct):
    consumer: str = msgspec.field(name='X-API-Consumer')


@final
class UserController(
    Controller[MsgspecSerializer],
    Body[UserModel],
    Headers[HeaderModel],
):
    @modify(validate_responses=False)  # <- now, we won't validate this endpoint
    def post(self) -> UserModel:
        if self.parsed_headers.consumer != 'my-api':
            # Notice that this response is never documented in the spec,
            # but, it won't raise a validation error, because validation is off
            raise APIError(
                {'detail': 'Wrong API consumer'},
                status_code=HTTPStatus.NOT_ACCEPTABLE,
            )
        # This response will be documented by default:
        return self.parsed_body
