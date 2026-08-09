from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class BillController(Controller[PydanticSerializer]):
    ignore_from_spec = True

    @modify(ignore_from_spec=True)
    async def get(self) -> str:
        return 'It works!'


# run: {"controller": "BillController", "method": "get", "url": "/api/username/"}  # noqa: ERA001, E501
# openapi: {"controller": "BillController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
