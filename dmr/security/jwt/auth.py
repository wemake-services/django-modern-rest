# A lot of code here is inspired by / taken from `litestar` project
# under a MIT license. See:
# https://github.com/litestar-org/litestar/blob/main/litestar/security/jwt/auth.py
# https://github.com/litestar-org/litestar/blob/main/LICENSE

from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects.components import Components
from dmr.openapi.objects.security_requirement import SecurityRequirement
from dmr.openapi.objects.security_scheme import SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.security.jwt.token import JWTToken

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class _BaseJWTAuth:  # noqa: WPS214, WPS230
    __slots__ = (
        'accepted_audiences',
        'accepted_issuers',
        'algorithm',
        'auth_header',
        'auth_scheme',
        'enforce_minimum_key_length',
        'leeway',
        'require_claims',
        'secret',
        'security_scheme_name',
        'strict_audience',
        'token_cls',
        'user_id_field',
        'verify_expiry',
        'verify_issued_at',
        'verify_jwt_id',
        'verify_not_before',
        'verify_subject',
    )

    def __init__(  # noqa: WPS211
        self,
        *,
        user_id_field: str = 'pk',
        algorithm: str = 'HS256',
        security_scheme_name: str = 'jwt',
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        secret: str | None = None,
        token_cls: type[JWTToken] = JWTToken,
        leeway: int = 0,  # seconds
        accepted_audiences: str | Sequence[str] | None = None,
        accepted_issuers: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_expiry: bool = True,
        verify_issued_at: bool = True,
        verify_jwt_id: bool = True,
        verify_not_before: bool = True,
        verify_subject: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        What can be modified?

        - *user_id_field* can be changed, it is used to get user model.
          By default we search by ``pk``, but it can be changed to be ``email``
          or any other unique user key.
        - *secret* can be changed, by default we use ``settings.SECRET_KEY``,
          but if you need some other secret for signing tokens - it is possible.
        - *token_cls* can use :class:`django_modern_rest.security.jwt.JWTToken`
          subclasses with different behavior.

        See :meth:`django_modern_rest.security.jwt.JWTToken.decode`
        for the docs for all jwt parameters explanation.
        """
        from django.conf import settings  # noqa: PLC0415

        self.user_id_field = user_id_field
        self.algorithm = algorithm
        self.security_scheme_name = security_scheme_name
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.secret: str = secret or settings.SECRET_KEY
        self.token_cls = token_cls
        self.leeway = leeway
        self.accepted_audiences = accepted_audiences
        self.accepted_issuers = accepted_issuers
        self.require_claims = require_claims
        self.verify_expiry = verify_expiry
        self.verify_issued_at = verify_issued_at
        self.verify_jwt_id = verify_jwt_id
        self.verify_not_before = verify_not_before
        self.verify_subject = verify_subject
        self.strict_audience = strict_audience
        self.enforce_minimum_key_length = enforce_minimum_key_length

    @property
    def security_scheme(self) -> Components:
        """Provides a security schema definition."""
        return Components(
            security_schemes={
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    scheme=self.auth_scheme,
                    name=self.auth_header,
                    bearer_format='JWT',
                    description='JWT token auth',
                ),
            },
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def prepare_token(self, request: HttpRequest) -> JWTToken | None:
        """Fetches JWTToken instance from the auth header."""
        # We return `None` here, because it might be some other auth.
        # We don't want to falsely trigger any errors just yet.
        header = self.get_header(request)
        if header is None:
            return None
        encoded_token = self.split_encoded_token(header)
        if encoded_token is None:
            return None
        # After this point we are sure that this is a jwt token.
        # We can raise `NotAuthenticatedError` below this point.
        return self.decode_token(encoded_token)

    def get_header(self, request: HttpRequest) -> str | None:
        """Gets the header with the token."""
        return request.headers.get(self.auth_header)

    def split_encoded_token(self, header: str) -> str | None:
        """Splits string like 'Bearer token' and returns 'token' part."""
        parts = header.split(' ')
        if len(parts) != 2 or parts[0] != self.auth_scheme:
            return None
        return parts[1]

    def decode_token(self, encoded_token: str) -> JWTToken:
        """Decodes token object from the encoded string."""
        return self.token_cls.decode(
            encoded_token=encoded_token,
            secret=self.secret,
            algorithm=self.algorithm,
            leeway=self.leeway,
            accepted_audiences=self.accepted_audiences,
            accepted_issuers=self.accepted_issuers,
            require_claims=self.require_claims,
            verify_exp=self.verify_expiry,
            verify_iat=self.verify_issued_at,
            verify_jti=self.verify_jwt_id,
            verify_nbf=self.verify_not_before,
            verify_sub=self.verify_subject,
            strict_audience=self.strict_audience,
            enforce_minimum_key_length=self.enforce_minimum_key_length,
        )

    def claim_from_token(self, token: JWTToken) -> str:
        """
        Return claim value from the token object.

        Override this method if you want to change how
        claim is extracted from token.
        For example, if you create ``email`` claim,
        it will be stored in ``.extras``.

        So, you would need to use: ``token.extras['email']``.
        """
        return token.sub

    def set_request_user(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
    ) -> None:
        """Set current user as authed for this request."""
        request.user = user


class JWTSyncAuth(_BaseJWTAuth, SyncAuth):
    """Sync jwt auth."""

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> 'AbstractBaseUser | None':
        """Does check for the correct jwt token."""
        token = self.prepare_token(controller.request)
        if token is None:
            return None
        return self.authenticate(controller.request, token)

    def authenticate(
        self,
        request: HttpRequest,
        token: JWTToken,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        user = self.get_user(token)
        self.check_auth(user, token)
        self.set_request_user(request, user)
        return user

    def get_user(self, token: JWTToken) -> 'AbstractBaseUser':
        """Get application user from token."""
        # We import user here, because we need this file to be importable
        # without calling `.setup()`:
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(**{
                self.user_id_field: self.claim_from_token(token),
            })
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None

    def check_auth(self, user: 'AbstractBaseUser', token: JWTToken) -> None:
        """Run extra auth checks, raise if something is wrong."""
        if not user.is_active:
            raise NotAuthenticatedError


class JWTAsyncAuth(_BaseJWTAuth, AsyncAuth):
    """Async jwt auth."""

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> 'AbstractBaseUser | None':
        """Does check for the correct jwt token."""
        token = self.prepare_token(controller.request)
        if token is None:
            return None
        return await self.authenticate(controller.request, token)

    async def authenticate(
        self,
        request: HttpRequest,
        token: JWTToken,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        user = await self.get_user(token)
        await self.check_auth(user, token)
        self.set_request_user(request, user)
        return user

    async def get_user(self, token: JWTToken) -> 'AbstractBaseUser':
        """Get application user from token."""
        # We import user here, because we need this file to be importable
        # without calling `.setup()`:
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(**{
                self.user_id_field: self.claim_from_token(token),
            })
        except ObjectDoesNotExist:
            raise NotAuthenticatedError from None

    async def check_auth(
        self,
        user: 'AbstractBaseUser',
        token: JWTToken,
    ) -> None:
        """Run extra auth checks, raise if something is wrong."""
        if not user.is_active:
            raise NotAuthenticatedError
