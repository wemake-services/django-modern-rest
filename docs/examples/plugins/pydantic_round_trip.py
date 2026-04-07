from typing import ClassVar

import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.plugins.pydantic.serializer import ToJsonKwargs


class _User(pydantic.BaseModel):
    username: str
    settings: pydantic.Json[dict[str, str]]


class _RoundTripPydantic(PydanticFastSerializer):
    to_json_kwargs: ClassVar[ToJsonKwargs] = {
        **PydanticFastSerializer.to_json_kwargs,
        'round_trip': True,
    }


class UserController(Controller[_RoundTripPydantic]):
    def post(self, parsed_body: Body[_User]) -> _User:
        return parsed_body


# run: {"controller": "UserController", "url": "/api/users/", "method": "post", "body": {"username": "sobolevn", "settings": "{\"status\": \"active\"}"}}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
