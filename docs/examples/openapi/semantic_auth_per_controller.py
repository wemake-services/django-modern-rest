from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    auth = (HeaderJWTSyncAuth(),)
    semantic_auth = False

    def get(self) -> str:
        return 'will not have semantic auth'

    def post(self) -> str:
        return 'will not have semantic auth'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
