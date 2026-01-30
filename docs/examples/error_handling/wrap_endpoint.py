from http import HTTPStatus

import pydantic
from django.http import HttpResponse

from django_modern_rest import Body, Controller, modify
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.errors import wrap_handler
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer


class TwoNumbers(pydantic.BaseModel):
    left: int
    right: int


class MathController(Controller[PydanticSerializer], Body[TwoNumbers]):
    def division_error(  # <- we define an error handler
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ZeroDivisionError):
            # This response's schema was automatically added
            # by `response_from_components = True` setting:
            return controller.to_error(
                {'detail': controller.serializer.error_serialize(str(exc))},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        # Reraise unfamiliar errors to let someone
        # else to handle them further.
        raise exc

    @modify(
        error_handler=wrap_handler(  # <- and we pass the handler
            division_error,
        ),
    )
    def patch(self) -> float:  # <- has custom error handling
        return self.parsed_body.left / self.parsed_body.right

    def post(self) -> float:  # <- has only default error handling
        return self.parsed_body.left * self.parsed_body.right


# run: {"controller": "MathController", "method": "patch", "body": {"left": 1, "right": 0}, "url": "/api/math/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
