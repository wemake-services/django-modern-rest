from typing import Self

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.exceptions import NotAuthenticatedError
from dmr.security import AsyncAuth
from dmr.serializer import BaseSerializer
from examples.auth.custom.auth import BaseProxyHeaderAuth


class ProxyHeaderAsyncAuth(BaseProxyHeaderAuth, AsyncAuth):
    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        username = self.get_username(controller.request)
        if not username:
            return None
        self.set_request_attrs(
            controller.request,
            await self.get_user(username),
        )
        return self

    async def get_user(self, username: str) -> AbstractBaseUser:
        try:
            return await get_user_model().objects.aget(
                username=username,
                is_active=True,
            )
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None
