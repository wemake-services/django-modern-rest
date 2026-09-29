from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.security.jwt import HeaderJWTSyncAuth


class APIController(Controller[PydanticFastSerializer]):
    auth = (HeaderJWTSyncAuth(), DjangoSessionSyncAuth())
    exclude_semantic_auth = frozenset(('jwt',))

    def get(self) -> str:
        return 'will not have jwt semantic auth'

    def post(self) -> str:
        return 'will not have jwt semantic auth'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
