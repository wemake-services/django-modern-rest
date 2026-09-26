from http import HTTPStatus
from typing import Final

from django.http import HttpResponse

from dmr import ResponseSpec
from dmr.controller import Controller
from dmr.endpoint import ValidateEndpoint
from dmr.plugins.pydantic import PydanticFastSerializer
from examples.reusable_code.extras_model import SmartResponse

#: Same as :data:`dmr.validate`, but supports ``extras=SmartResponse(...)``.
validate: Final = ValidateEndpoint(SmartResponse)


class APIController(Controller[PydanticFastSerializer]):
    extras = SmartResponse(response_text='from controller')

    @validate(
        ResponseSpec(str, status_code=HTTPStatus.OK),
        extras=SmartResponse(response_text='from endpoint'),
    )
    def get(self) -> HttpResponse:
        return self.to_response(SmartResponse.of(self))

    @validate(ResponseSpec(str, status_code=HTTPStatus.CREATED))
    def post(self) -> HttpResponse:  # controller level extras
        return self.to_response(SmartResponse.of(self))


# run: {"controller": "APIController", "method": "get", "url": "/api/example/"}  # noqa: ERA001
# run: {"controller": "APIController", "method": "post", "url": "/api/example/"}  # noqa: ERA001
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
