from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer


class APIController(Controller[PydanticFastSerializer]):
    semantic_responses = False

    async def get(self) -> str:
        return 'will not have semantic responses'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
