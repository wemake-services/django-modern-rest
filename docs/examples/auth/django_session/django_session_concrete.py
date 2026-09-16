from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session.concrete_views import (
    DjangoSessionSyncController,
)


# You can also use `DjangoSessionAsyncController` if needed:
class SessionController(DjangoSessionSyncController[PydanticSerializer]):
    """Authenticates a user and starts a django session."""


# run: {"controller": "SessionController", "method": "post", "url": "/api/auth/", "body" :{"username": "test_user", "password": "password"}, "curl_args": ["-D", "-"], "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "SessionController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
