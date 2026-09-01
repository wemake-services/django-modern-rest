from typing import Final, Self

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security import SyncAuth
from dmr.serializer import BaseSerializer

#: Header that our authenticating proxy sets for every request it lets in.
PROXY_USER_HEADER: Final = 'X-Forwarded-User'


class BaseProxyHeaderAuth:
    """Everything that does not depend on sync or async execution."""

    __slots__ = ('header_name', 'security_scheme_name')

    def __init__(
        self,
        *,
        header_name: str = PROXY_USER_HEADER,
        security_scheme_name: str = 'proxy_user',
    ) -> None:
        self.header_name = header_name
        self.security_scheme_name = security_scheme_name

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.header_name,
                security_scheme_in='header',
                description='Username of the already authenticated user',
            ),
        }

    @property
    def security_requirement(self) -> SecurityRequirement:
        return {self.security_scheme_name: []}

    def get_username(self, request: HttpRequest) -> str | None:
        return request.headers.get(self.header_name)

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        request.user = user

        # Needed even for sync auth, so `await request.auser()` keeps
        # working in `sync_to_async` and other mixed contexts:
        async def auser() -> AbstractBaseUser:  # noqa: WPS430
            return user

        request.auser = auser


class ProxyHeaderSyncAuth(BaseProxyHeaderAuth, SyncAuth):
    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        username = self.get_username(controller.request)
        if not username:
            # The header is missing, so this auth simply does not apply.
            # Return `None`, so the next auth in the chain can try.
            return None
        # The header is here, so the client did mean to use this auth.
        # From now on any problem is an error, not a reason to fall through.
        self.set_request_attrs(controller.request, self.get_user(username))
        return self

    def get_user(self, username: str) -> AbstractBaseUser:
        try:
            return get_user_model().objects.get(
                username=username,
                is_active=True,
            )
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None
