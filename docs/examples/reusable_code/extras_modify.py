from typing import Final

from dmr.controller import Controller
from dmr.endpoint import ModifyEndpoint
from dmr.plugins.pydantic import PydanticFastSerializer
from examples.reusable_code.extras_model import SmartResponse

#: Same as :data:`dmr.modify`, but supports ``extras=SmartResponse(...)``.
modify: Final = ModifyEndpoint(SmartResponse)


class APIController(Controller[PydanticFastSerializer]):
    extras = SmartResponse(response_text='from controller')

    def get(self) -> str:
        return SmartResponse.of(self)

    @modify(extras=SmartResponse(response_text='from endpoint'))
    def post(self) -> str:
        return SmartResponse.of(self)


# run: {"controller": "APIController", "method": "get", "url": "/api/example/"}  # noqa: ERA001
# run: {"controller": "APIController", "method": "post", "url": "/api/example/"}  # noqa: ERA001
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
