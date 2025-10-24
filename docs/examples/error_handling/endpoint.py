from http import HTTPStatus

import pydantic
from django.http import HttpResponse

from django_modern_rest import (
    Body,
    Controller,
    modify,
)
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.plugins.pydantic import (
    PydanticSerializer,
)


class TwoNumbers(pydantic.BaseModel):
    left: int
    right: int


class MathController(Controller[PydanticSerializer], Body[TwoNumbers]):
    def division_error(  # <- we define an error handler
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ZeroDivisionError):
            # This response's schema was automatically added
            # by `response_from_components = True` setting:
            return self.to_error(
                {'detail': self.serializer.error_serialize(str(exc))},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        # Reraise unfamiliar errors to let someone
        # else to handle them further.
        raise exc

    @modify(error_handler=division_error)  # <- and we pass the handler
    def get(self) -> float:  # <- has custom error handling
        return self.parsed_body.left / self.parsed_body.right

    def post(self) -> float:  # <- has only default error handling
        return self.parsed_body.left * self.parsed_body.right
