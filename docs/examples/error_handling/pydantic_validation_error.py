from typing import Literal

import pydantic

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class Pong(pydantic.BaseModel):
    message: Literal['pong']


class PongController(Controller[PydanticSerializer]):
    def get(self) -> Pong:
        # This will trigger `pydantic.ValidationError`,
        # because `message` must be `'pong'`, not `'wrong'`:
        return Pong(message='wrong')


# run: {"controller": "PongController", "method": "get", "url": "/api/ping/", "curl_args": ["-D", "-"], "assert-error-text": "Internal server error", "fail-with-body": false}  # noqa: ERA001, E501
