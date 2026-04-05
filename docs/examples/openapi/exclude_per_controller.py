from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class APIController(Controller[PydanticSerializer]):
    exclude_semantic_responses = frozenset((422,))

    async def get(self) -> str:
        return 'will not have semantic response with 422 status code'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
