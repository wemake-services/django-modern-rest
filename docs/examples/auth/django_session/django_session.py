from typing import final

from typing_extensions import override

from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.django_session.views import (
    DjangoSessionPayload,
    DjangoSessionResponse,
    DjangoSessionSyncController,
)


@final
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
