from typing import Final, final

from typing_extensions import override

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from django_modern_rest.security.django_session.views import (
    DjangoSessionAsyncController,
    DjangoSessionPayload,
    DjangoSessionResponse,
    DjangoSessionSyncController,
)

_USER_ID: Final = 'user_id'


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
        return {_USER_ID: str(self.request.user.pk)}


@final
class SessionAsyncController(
    DjangoSessionAsyncController[
        PydanticSerializer,
        DjangoSessionPayload,
        DjangoSessionResponse,
    ],
):
    @override
    async def convert_auth_payload(
        self,
        payload: DjangoSessionPayload,
    ) -> DjangoSessionPayload:
        return payload

    @override
    async def make_api_response(self) -> DjangoSessionResponse:
        return {_USER_ID: str(self.request.user.pk)}


@final
class UserSyncController(Controller[PydanticSerializer]):
    auth = (DjangoSessionSyncAuth(),)

    def get(self) -> DjangoSessionResponse:
        return {_USER_ID: str(self.request.user.pk)}


@final
class UserAsyncController(Controller[PydanticSerializer]):
    auth = (DjangoSessionAsyncAuth(),)

    async def get(self) -> DjangoSessionResponse:
        return {_USER_ID: str(self.request.user.pk)}
