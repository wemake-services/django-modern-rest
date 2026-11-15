from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    @modify(
        auth=[HeaderJWTSyncAuth()],
        semantic_auth=False,
        exclude_semantic_responses={HTTPStatus.UNAUTHORIZED},
    )
    def post(self) -> str:
        return 'will not have semantic auth and no 401 response'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
