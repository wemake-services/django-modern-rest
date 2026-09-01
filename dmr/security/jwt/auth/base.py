# A lot of code here is inspired by / taken from `litestar` project
# under a MIT license. See:
# https://github.com/litestar-org/litestar/blob/main/litestar/security/jwt/auth.py
# https://github.com/litestar-org/litestar/blob/main/LICENSE

from abc import abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Literal, Self, overload

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import SecurityRequirement
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.security.jwt.token import JWToken

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

# Errors that mean "this token subject cannot identify a user".
#
# A signed token can carry anything at all in its claims, while
# the user lookup field is typed. Django raises `ValueError` when
# an integer column gets a non-numeric value, and `ValidationError`
# from fields like `UUIDField` that validate on conversion.
# All of them mean the same thing for us: no such user.
USER_LOOKUP_ERRORS: Final = (
    ObjectDoesNotExist,
    ValidationError,
    TypeError,
    ValueError,
)


class _BaseJWTAuth:  # noqa: WPS214, WPS230
    """
    Transport-agnostic part of jwt auth.

    Knows how to decode and validate a token,
    but not where the token comes from.
    Subclasses define the transport by implementing
    :meth:`get_token_from_request` and :meth:`split_encoded_token`.
    """

    __slots__ = (
        'accepted_audiences',
        'accepted_issuers',
        'algorithm',
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
        secret: str | None = None,
        token_cls: type[JWToken] = JWToken,
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
        - *token_cls* can use :class:`dmr.security.jwt.token.JWToken`
          subclasses with different behavior.

        See :meth:`dmr.security.jwt.token.JWToken.decode`
        for the docs for all jwt parameters explanation.
        """
        from django.conf import settings  # noqa: PLC0415

        self.user_id_field = user_id_field
        self.algorithm = algorithm
        self.security_scheme_name = security_scheme_name
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
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def prepare_token(self, request: HttpRequest) -> JWToken | None:
        """Fetches JWToken instance from the request."""
        # We return `None` here, because it might be some other auth.
        # We don't want to falsely trigger any errors just yet.
        token = self.get_token_from_request(request)
        if token is None:
            return None
        encoded_token = self.split_encoded_token(token)
        if encoded_token is None:
            return None
        # After this point we are sure that this is a jwt token.
        # We can raise `NotAuthenticatedError` below this point.
        return self.decode_token(encoded_token)

    @abstractmethod
    def get_token_from_request(self, request: HttpRequest) -> str | None:
        """Gets the raw jwt token from the request. Must be overridden."""
        raise NotImplementedError

    @abstractmethod
    def split_encoded_token(self, header: str) -> str | None:
        """Extracts the encoded token from a raw value. Must be overridden."""
        raise NotImplementedError

    def decode_token(self, encoded_token: str) -> JWToken:
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

    def claim_from_token(self, token: JWToken) -> str:
        """
        Return claim value from the token object.

        Override this method if you want to change how
        claim is extracted from token.
        For example, if you create ``email`` claim,
        it will be stored in ``.extras``.

        So, you would need to use: ``token.extras['email']``.
        """
        return token.sub


class BaseJWTSyncAuth(_BaseJWTAuth, SyncAuth):
    """
    Shared sync authentication pipeline for jwt auth.

    Subclass this to add a jwt transport we don't ship out of the box.

    .. versionadded:: 0.15.0
    """

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does check for the correct jwt token."""
        token = self.prepare_token(controller.request)
        if token is None:
            return None
        self.authenticate(controller.request, token)
        return self

    def authenticate(
        self,
        request: HttpRequest,
        token: JWToken,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        user = self.get_user(token)
        self.check_auth(user, token)
        self.set_request_attrs(request, user, token)
        return user

    def get_user(self, token: JWToken) -> 'AbstractBaseUser':
        """Get application user from token."""
        # We import user here, because we need this file to be importable
        # without calling `.setup()`:
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(
                **{
                    self.user_id_field: self.claim_from_token(token),
                },
            )
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    def check_auth(self, user: 'AbstractBaseUser', token: JWToken) -> None:
        """Run extra auth checks, raise if something is wrong."""
        if not user.is_active:
            raise NotAuthenticatedError

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user, token=token)


class BaseJWTAsyncAuth(_BaseJWTAuth, AsyncAuth):
    """
    Shared async authentication pipeline for jwt auth.

    Subclass this to add a jwt transport we don't ship out of the box.

    .. versionadded:: 0.15.0
    """

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does check for the correct jwt token."""
        token = self.prepare_token(controller.request)
        if token is None:
            return None
        await self.authenticate(controller.request, token)
        return self

    async def authenticate(
        self,
        request: HttpRequest,
        token: JWToken,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        user = await self.get_user(token)
        await self.check_auth(user, token)
        await self.set_request_attrs(request, user, token)
        return user

    async def get_user(self, token: JWToken) -> 'AbstractBaseUser':
        """Get application user from token."""
        # We import user here, because we need this file to be importable
        # without calling `.setup()`:
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(
                **{
                    self.user_id_field: self.claim_from_token(token),
                },
            )
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    async def check_auth(
        self,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None:
        """Run extra auth checks, raise if something is wrong."""
        if not user.is_active:
            raise NotAuthenticatedError

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        token: JWToken,
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user, token=token)


@overload
def request_jwt(request: HttpRequest, *, strict: Literal[True]) -> JWToken: ...


@overload
def request_jwt(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> JWToken | None: ...


def request_jwt(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> JWToken | None:
    """
    Returns a JWToken from request, if it was authed with it.

    When *strict* is passed and *request* has no jwt token,
    we raise :exc:`AttributeError`.
    """
    jwt = getattr(request, '__dmr_jwt__', None)
    if jwt is None and strict:
        raise AttributeError('__dmr_jwt__')
    return jwt


def set_request_attrs(
    request: HttpRequest,
    user: 'AbstractBaseUser',
    *,
    token: JWToken | None = None,
) -> None:
    """Set all required properties to the authed request."""
    request.user = user

    # This is needed even for sync views for consistency,
    # and wild `async_to_sync` / `sync_to_async` use-cases:

    async def auser() -> 'AbstractBaseUser':  # noqa: WPS430
        return user

    request.auser = auser

    if token is not None:
        request.__dmr_jwt__ = token  # type: ignore[attr-defined]
