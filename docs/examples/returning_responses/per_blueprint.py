from http import HTTPStatus
from typing import ClassVar, final

import msgspec

from django_modern_rest import APIError, Blueprint, Body, Headers
from django_modern_rest.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    email: str


class HeaderModel(msgspec.Struct):
    consumer: str = msgspec.field(name='X-API-Consumer')


@final
class UserBlueprint(
    Blueprint[MsgspecSerializer],
    Body[UserModel],
    Headers[HeaderModel],
):
    # Now, we won't validate all endpoints in this blueprint:
    validate_responses: ClassVar[bool | None] = False

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
