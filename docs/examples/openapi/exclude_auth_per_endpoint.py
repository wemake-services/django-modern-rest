from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    auth = (HeaderJWTSyncAuth(), DjangoSessionSyncAuth())

    def get(self) -> str:
        return 'will have all semantic auth'

    @modify(exclude_semantic_auth={'jwt'})
    def post(self) -> str:
        return 'will not have jwt semantic auth'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
