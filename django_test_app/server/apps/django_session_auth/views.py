from typing import Final, final

from django.views.decorators.debug import sensitive_variables
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from dmr.security.django_session.views import (
    DjangoSessionAsyncController,
    DjangoSessionPayload,
    DjangoSessionResponse,
    DjangoSessionSyncController,
)
from server.common.assertions import check_sensitive_parameters

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
        check_sensitive_parameters(self.request)
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
    @sensitive_variables()
    async def convert_auth_payload(
        self,
        payload: DjangoSessionPayload,
    ) -> DjangoSessionPayload:
        check_sensitive_parameters(self.request)
        return payload

    @override
    async def make_api_response(self) -> DjangoSessionResponse:
        return {_USER_ID: str((await self.request.auser()).pk)}


@final
class UserSyncController(Controller[PydanticSerializer]):
    auth = (DjangoSessionSyncAuth(),)

    def get(self) -> DjangoSessionResponse:
        return {_USER_ID: str(self.request.user.pk)}


@final
class UserAsyncController(Controller[PydanticSerializer]):
    auth = (DjangoSessionAsyncAuth(),)

    async def get(self) -> DjangoSessionResponse:
        return {_USER_ID: str((await self.request.auser()).pk)}
