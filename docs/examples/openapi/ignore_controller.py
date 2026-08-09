from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class BillController(Controller[PydanticSerializer]):
    ignore_from_spec = True

    def get(self) -> str:
        return 'It is hidden'

    @modify(ignore_from_spec=False)
    def post(self) -> str:
        return 'It is in OpenAPI'


# run: {"controller": "BillController", "method": "get", "url": "/api/username/"}  # noqa: ERA001, E501
# run: {"controller": "BillController", "method": "post", "url": "/api/username/"}  # noqa: ERA001, E501
# openapi: {"controller": "BillController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
