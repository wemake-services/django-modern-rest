from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.token.app.models import Token
from dmr.security.token.concrete_views import ObtainTokenSyncController


# You can also use `ObtainTokenAsyncController` if needed:
class ObtainTokenController(ObtainTokenSyncController[PydanticSerializer]):
    """Authenticates a user and issues a new opaque token."""

    # Specifying `token_cls` is the only thing left to do:
    token_cls = Token


# run: {"controller": "ObtainTokenController", "method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "ObtainTokenController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
