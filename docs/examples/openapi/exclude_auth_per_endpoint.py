from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    auth = (HeaderJWTSyncAuth(),)

    def get(self) -> str:
        return 'will not have semantic auth'

    @modify(exclude_semantic_auth={'jwt'})
    def post(self) -> str:
        return 'will not have semantic auth'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
