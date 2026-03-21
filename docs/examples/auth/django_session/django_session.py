from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session.views import (
    DjangoSessionPayload,
    DjangoSessionResponse,
    DjangoSessionSyncController,
)


class SessionSyncController(
    DjangoSessionSyncController[
        PydanticSerializer,
        DjangoSessionPayload,
        DjangoSessionResponse,
    ],
):
    @override
    def convert_auth_payload(
        self,
        payload: DjangoSessionPayload,
    ) -> DjangoSessionPayload:
        return payload

    @override
    def make_api_response(self) -> DjangoSessionResponse:
        return {'user_id': str(self.request.user.pk)}


# run: {"controller": "SessionSyncController", "method": "post", "url": "/api/auth/", "body" :{"username": "test_user", "password": "password"}, "curl_args": ["-D", "-"], "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "SessionSyncController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
