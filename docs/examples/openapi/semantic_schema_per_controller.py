from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    auth = (HeaderJWTSyncAuth(),)
    semantic_schema = False

    def get(self) -> str:
        return 'will not have semantic schema at all'

    def post(self) -> str:
        return 'will not have semantic schema at all'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
