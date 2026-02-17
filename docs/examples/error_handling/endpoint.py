from http import HTTPStatus

import pydantic
from django.http import HttpResponse

from dmr import Body, Controller, modify
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer


class TwoNumbers(pydantic.BaseModel):
    left: int
    right: int


def division_error(  # <- we define an error handler
    endpoint: Endpoint,
    controller: Controller[BaseSerializer],
    exc: Exception,
) -> HttpResponse:
    if isinstance(exc, ZeroDivisionError):
        # This response's schema was automatically added by `Body`:
        return controller.to_error(
            controller.format_error(str(exc)),
            status_code=HTTPStatus.BAD_REQUEST,
        )
    # Reraise unfamiliar errors to let someone
    # else to handle them further.
    raise exc


class MathController(Controller[PydanticSerializer], Body[TwoNumbers]):
    @modify(error_handler=division_error)  # <- and we pass the handler
    def patch(self) -> float:  # <- has custom error handling
        return self.parsed_body.left / self.parsed_body.right

    def post(self) -> float:  # <- has only default error handling
        return self.parsed_body.left * self.parsed_body.right


# run: {"controller": "MathController", "method": "patch", "body": {"left": 1, "right": 0}, "url": "/api/math/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
