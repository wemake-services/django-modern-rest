from http import HTTPStatus
from typing import Literal

import pydantic
from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller, ResponseSpec
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer


class Pong(pydantic.BaseModel):
    message: Literal['pong']


class PongController(Controller[PydanticSerializer]):
    responses = (
        ResponseSpec(
            Controller.error_model,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ),
    )

    def get(self) -> Pong:
        # This will trigger `pydantic.ValidationError`,
        # because `message` must be `'pong'`, not `'wrong'`:
        return Pong(message='wrong')

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, pydantic.ValidationError):
            # Now, handle the error, but do not show what actually happened
            # to the outside world, it might contain sensitive data:
            return self.to_response(
                self.format_error('Validation error'),
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        return super().handle_error(endpoint, controller, exc)


# run: {"controller": "PongController", "method": "get", "url": "/api/ping/", "curl_args": ["-D", "-"], "assert-error-text": "Validation error", "fail-with-body": false}  # noqa: ERA001, E501
