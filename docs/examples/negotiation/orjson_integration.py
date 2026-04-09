import orjson  # type: ignore[import-not-found, unused-ignore]
import pydantic

from dmr import Body, Controller
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer


class _UserInputData(pydantic.BaseModel):
    email: pydantic.EmailStr


class UserController(Controller[PydanticSerializer]):
    parsers = (JsonParser(json_module=orjson),)
    renderers = (JsonRenderer(json_module=orjson),)

    def post(
        self,
        parsed_body: Body[_UserInputData],
    ) -> _UserInputData:
        return parsed_body


# run: {"controller": "UserController", "method": "post", "url": "/api/user/", "body": {"email": "user@example.com"}}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
