from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class APIController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'will have semantic responses'

    @modify(semantic_responses=False)
    def post(self) -> str:
        return 'will not have semantic responses'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
