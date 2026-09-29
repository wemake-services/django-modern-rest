from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    auth = (HeaderJWTSyncAuth(),)

    def get(self) -> str:
        return 'will have semantic schema'

    @modify(semantic_schema=False)
    def post(self) -> str:
        return 'will not have semantic schema at all'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
