import dataclasses
import datetime as dt
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Generic,
    Literal,
    TypeAlias,
)

from django.conf import settings
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import rotate_token
from django.views.decorators.debug import (
    sensitive_post_parameters,
    sensitive_variables,
)
from typing_extensions import TypeVar

from dmr import Body, CookieSpec, NewCookie, ResponseSpec, validate
from dmr.decorators import endpoint_decorator
from dmr.endpoint import ValidateAnyCallable
from dmr.errors import ErrorModel
from dmr.exceptions import EndpointMetadataError, NotAuthenticatedError
from dmr.headers import HeaderSpec
from dmr.internal.csrf import ensure_csrf
from dmr.security.base import NO_STORE_HEADERS
from dmr.security.jwt.auth.base import USER_LOOKUP_ERRORS, set_request_attrs
from dmr.security.jwt.auth.cookie import (
    DEFAULT_ACCESS_COOKIE,
    DEFAULT_REFRESH_COOKIE,
)
from dmr.security.jwt.token import JWToken
from dmr.security.jwt.views.base import (
    BaseRefreshTokenController,
    BaseTokenController,
    ObtainTokensPayload,
)
from dmr.serializer import BaseSerializer
from dmr.types import safe_typevar

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

#: Request body of all the controllers that authenticate a user.
_ObtainTokensT = TypeVar('_ObtainTokensT', bound=Mapping[str, Any])
_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)

#: Cookie views send their tokens in cookies, the body is empty by default.
_CookieResponseT = TypeVar('_CookieResponseT', default=None)

_SameSite: TypeAlias = Literal['lax', 'strict', 'none']

# `_CookieResponseT` as a value, so it can be passed to `ResponseSpec`.
# It is resolved to the real type of each final controller later on:
_COOKIE_RESPONSE_TYPE: Final = safe_typevar('_CookieResponseT')

# `@validate` describes headers and sets them by hand,
# both parts are built from `NO_STORE_HEADERS`, so they can't diverge:
_NO_STORE_SPEC: Final = MappingProxyType({
    header_name: header.to_spec()
    for header_name, header in NO_STORE_HEADERS.items()
})
_NO_STORE_VALUES: Final = MappingProxyType({
    header_name: header.value
    for header_name, header in NO_STORE_HEADERS.items()
})


class _BaseCookieTokensController(  # noqa: WPS214
    BaseTokenController[_SerializerT],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Base for all the controllers that issue jwt tokens as cookies.

    Cookie flags are the whole security surface of this flow,
    so we pick safe defaults and never let the description
    and the actual cookie diverge: both are built
    from the same :class:`~dmr.cookies.CookieSpec` instance.

    Attributes:
        jwt_access_cookie: Name of the cookie with the access token.
            Must match ``cookie_name``
            of :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth`
            that reads it back.
        jwt_refresh_cookie: Name of the cookie with the refresh token.
        jwt_access_cookie_path: ``path`` of the access token cookie,
            it is sent to your whole API by default.
        jwt_refresh_cookie_path: ``path`` of the refresh token cookie.
            Has no default on purpose: set it to the url of the endpoint
            that refreshes tokens, so the refresh token is not sent
            with any other request. Pass ``'/'`` to send it everywhere.
        jwt_cookie_domain: ``domain`` of both cookies.
        jwt_cookie_secure: Only send both cookies over https.
        jwt_cookie_httponly: Hide both cookies from javascript.
        jwt_cookie_samesite: ``samesite`` policy of both cookies.
            Do not weaken it to ``'none'`` unless your frontend
            really is on another site.
        jwt_ensure_csrf: Run the CSRF check on endpoints that act
            on cookies alone, without any credentials in the body.

    .. versionadded:: 0.15.0
    """

    jwt_access_cookie: ClassVar[str] = DEFAULT_ACCESS_COOKIE
    jwt_refresh_cookie: ClassVar[str] = DEFAULT_REFRESH_COOKIE
    jwt_access_cookie_path: ClassVar['_StrOrPromise'] = '/'
    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = None
    jwt_cookie_domain: ClassVar[str | None] = None
    jwt_cookie_secure: ClassVar[bool] = True
    jwt_cookie_httponly: ClassVar[bool] = True
    jwt_cookie_samesite: ClassVar[_SameSite] = 'lax'
    jwt_ensure_csrf: ClassVar[bool] = True

    @classmethod
    def access_cookie_spec(cls) -> CookieSpec:
        """Describes the cookie that carries the access token."""
        return CookieSpec(
            path=cls.jwt_access_cookie_path,
            max_age=int(cls.jwt_expiration.total_seconds()),
            domain=cls.jwt_cookie_domain,
            secure=cls.jwt_cookie_secure,
            httponly=cls.jwt_cookie_httponly,
            samesite=cls.jwt_cookie_samesite,
            description='Access token, sent with every API request.',
        )

    @classmethod
    def refresh_cookie_spec(cls) -> CookieSpec:
        """
        Describes the cookie that carries the refresh token.

        Raises:
            EndpointMetadataError: When ``jwt_refresh_cookie_path``
                is not set by the final controller.

        """
        if cls.jwt_refresh_cookie_path is None:
            raise EndpointMetadataError(
                f'{cls.__qualname__!r} must define `jwt_refresh_cookie_path`, '
                'it is the url path of your refresh endpoint. '
                'Scoping the refresh cookie to it keeps the refresh token '
                'out of all the other requests. '
                "Use '/' to send it everywhere.",
            )
        return CookieSpec(
            path=cls.jwt_refresh_cookie_path,
            max_age=int(cls.jwt_refresh_expiration.total_seconds()),
            domain=cls.jwt_cookie_domain,
            secure=cls.jwt_cookie_secure,
            httponly=cls.jwt_cookie_httponly,
            samesite=cls.jwt_cookie_samesite,
            description='Refresh token, only sent to the refresh endpoint.',
        )

    @classmethod
    def issued_cookies_spec(cls) -> dict[str, CookieSpec]:
        """Describes both token cookies of a successful response."""
        return {
            cls.jwt_access_cookie: cls.access_cookie_spec(),
            cls.jwt_refresh_cookie: cls.refresh_cookie_spec(),
        }

    @classmethod
    def discarded_cookies_spec(cls) -> dict[str, CookieSpec]:
        """Describes both token cookies as they are sent on logout."""
        return {
            cookie_name: dataclasses.replace(
                cookie_spec,
                max_age=0,
                description='Sent back empty and expired, so it is dropped.',
            )
            for cookie_name, cookie_spec in cls.issued_cookies_spec().items()
        }

    @classmethod
    def response_headers_spec(cls) -> Mapping[str, HeaderSpec]:
        """
        Describes the headers of every response this controller sends.

        Credentials must not be written to any cache, neither shared,
        nor local. Redefine it together with :meth:`response_headers`.
        """
        return _NO_STORE_SPEC

    def response_headers(self) -> Mapping[str, str]:
        """Headers of every response this controller sends."""
        return _NO_STORE_VALUES

    @classmethod
    def csrf_cookie_spec(cls) -> dict[str, CookieSpec]:
        """
        Describes the CSRF cookie that Django sets after us.

        It is written by :class:`django.middleware.csrf.CsrfViewMiddleware`
        once we rotate the token, which happens after our own validation.
        That is why it is only documented and never validated.
        With ``CSRF_USE_SESSIONS`` there is no such cookie at all.
        """
        if settings.CSRF_USE_SESSIONS:
            return {}
        return {
            settings.CSRF_COOKIE_NAME: CookieSpec(
                skip_validation=True,
                description='CSRF protection.',
            ),
        }

    @classmethod
    def csrf_response_specs(cls) -> tuple[ResponseSpec, ...]:
        """Describes the response of a failed CSRF check."""
        if not cls.jwt_ensure_csrf:
            return ()
        return (
            ResponseSpec(
                return_type=cls.error_model,
                status_code=HTTPStatus.FORBIDDEN,
                description='Raised when CSRF check failed',
            ),
        )

    def check_csrf(self) -> None:
        """
        Enforce CSRF for requests that are authed by a cookie alone.

        The browser sends these cookies on its own, so without this check
        any other site could refresh or drop the tokens of our users.
        Set ``jwt_ensure_csrf`` to ``False`` to opt out.
        """
        if self.jwt_ensure_csrf:
            ensure_csrf(self)

    @sensitive_variables()
    def issue_cookies(self) -> dict[str, NewCookie]:
        """Create both token cookies for the user of the current request."""
        now = dt.datetime.now(dt.UTC)
        return {
            self.jwt_access_cookie: NewCookie.from_spec(
                self.access_cookie_spec(),
                value=self.create_jwt_token(
                    expiration=now + self.jwt_expiration,
                    token_type='access',  # noqa: S106
                ),
            ),
            self.jwt_refresh_cookie: NewCookie.from_spec(
                self.refresh_cookie_spec(),
                value=self.create_jwt_token(
                    expiration=now + self.jwt_refresh_expiration,
                    token_type='refresh',  # noqa: S106
                ),
            ),
        }

    def discard_cookies(self) -> dict[str, NewCookie]:
        """Create empty cookies, so the browser drops the tokens right away."""
        discarded = self.discarded_cookies_spec()
        return {
            cookie_name: NewCookie.from_spec(cookie_spec, value='')
            for cookie_name, cookie_spec in discarded.items()
        }

    def rotate_csrf_token(self) -> None:
        """
        Issue a new CSRF token for the freshly authed user.

        This is what :func:`django.contrib.auth.login` does as well.
        Our cookie auth checks CSRF on every request it authenticates,
        and the frontend needs a fresh token to pass that check.
        """
        rotate_token(self.request)

    def get_cookie_token(self, cookie_name: str) -> str:
        """
        Read a raw jwt token from the given cookie.

        Raises:
            NotAuthenticatedError: When the cookie is missing or empty.

        """
        encoded_token = self.request.COOKIES.get(cookie_name)
        if not encoded_token:
            raise NotAuthenticatedError
        return encoded_token


class _BaseCookieTokensSyncController(
    _BaseCookieTokensController[_SerializerT, _CookieResponseT],
):
    """Sync half of the cookie controllers."""

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Mark the user of this request as authenticated."""
        set_request_attrs(request, user)

    def make_api_response(self) -> _CookieResponseT:
        """
        Build the response body that is sent next to the cookies.

        Empty by default: the tokens are already in the cookies,
        and sending them in the body as well would hand them
        to any script on the page, undoing ``httponly``.

        Change the response status code from ``204`` when you return a body.
        """
        # Tokens live in the cookies, so there is nothing to send here:
        return None  # type: ignore[return-value]


class _BaseCookieTokensAsyncController(
    _BaseCookieTokensController[_SerializerT, _CookieResponseT],
):
    """Async half of the cookie controllers."""

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: AbstractBaseUser,
    ) -> None:
        """Mark the user of this request as authenticated."""
        set_request_attrs(request, user)

    async def make_api_response(self) -> _CookieResponseT:
        """
        Build the response body that is sent next to the cookies.

        Empty by default: the tokens are already in the cookies,
        and sending them in the body as well would hand them
        to any script on the page, undoing ``httponly``.

        Change the response status code from ``204`` when you return a body.
        """
        # Tokens live in the cookies, so there is nothing to send here:
        return None  # type: ignore[return-value]


class CookieObtainTokensSyncController(
    _BaseCookieTokensSyncController[_SerializerT, _CookieResponseT],
    Generic[_SerializerT, _ObtainTokensT, _CookieResponseT],
):
    """
    Sync controller to issue access and refresh tokens as cookies.

    Works like :class:`~dmr.security.jwt.views.ObtainTokensSyncController`,
    but the tokens are set as cookies
    for :class:`~dmr.security.jwt.auth.CookieJWTSyncAuth` to read them back,
    instead of being returned in the response body.

    Setting ``jwt_refresh_cookie_path`` to the url
    of your refresh endpoint is required, everything else has a default.

    Attributes:
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default access token expiration timedelta,
            it is also the ``max-age`` of the access cookie.
        jwt_refresh_expiration: Default refresh token expiration timedelta,
            it is also the ``max-age`` of the refresh cookie.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the sync cookie login controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies={
                    **cls.issued_cookies_spec(),
                    **cls.csrf_cookie_spec(),
                },
            ),
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @validate.lazy(validate_spec)
    def post(self, parsed_body: Body[_ObtainTokensT]) -> HttpResponse:
        """By default cookies are acquired on post."""
        return self.login(parsed_body)

    def login(self, parsed_body: _ObtainTokensT) -> HttpResponse:
        """Perform the sync login routine and set the token cookies."""
        user = authenticate(
            self.request,
            **self.convert_auth_payload(parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        self.set_request_attrs(self.request, user)
        self.rotate_csrf_token()
        return self.to_response(
            self.make_api_response(),
            status_code=self.response_status_code,
            headers=self.response_headers(),
            cookies=self.issue_cookies(),
        )

    @abstractmethod
    def convert_auth_payload(
        self,
        payload: _ObtainTokensT,
    ) -> ObtainTokensPayload:
        """
        Convert your custom payload to the kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports, basically it needs
        ``username`` and ``password`` strings.
        """
        raise NotImplementedError


class CookieObtainTokensAsyncController(
    _BaseCookieTokensAsyncController[_SerializerT, _CookieResponseT],
    Generic[_SerializerT, _ObtainTokensT, _CookieResponseT],
):
    """
    Async controller to issue access and refresh tokens as cookies.

    Works like :class:`~dmr.security.jwt.views.ObtainTokensAsyncController`,
    but the tokens are set as cookies
    for :class:`~dmr.security.jwt.auth.CookieJWTAsyncAuth` to read them back,
    instead of being returned in the response body.

    Setting ``jwt_refresh_cookie_path`` to the url
    of your refresh endpoint is required, everything else has a default.

    Attributes:
        jwt_audiences: String or sequence of string of audiences for JWT token.
        jwt_issuer: String of who issued this JWT token.
        jwt_algorithm: Default algorithm to use for token signing.
        jwt_expiration: Default access token expiration timedelta,
            it is also the ``max-age`` of the access cookie.
        jwt_refresh_expiration: Default refresh token expiration timedelta,
            it is also the ``max-age`` of the refresh cookie.
        jwt_secret: Alternative token secret for signing.
            By default uses ``secret.SECRET_KEY``.
        jwt_token_cls: Possible custom JWT token class.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the async cookie login controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies={
                    **cls.issued_cookies_spec(),
                    **cls.csrf_cookie_spec(),
                },
            ),
        )

    @sensitive_variables()
    @endpoint_decorator(sensitive_post_parameters())
    @validate.lazy(validate_spec)
    async def post(self, parsed_body: Body[_ObtainTokensT]) -> HttpResponse:
        """By default cookies are acquired on post."""
        return await self.login(parsed_body)

    @sensitive_variables()
    async def login(self, parsed_body: _ObtainTokensT) -> HttpResponse:
        """Perform the async login routine and set the token cookies."""
        user = await aauthenticate(
            self.request,
            **(await self.convert_auth_payload(parsed_body)),
        )
        if user is None:
            raise NotAuthenticatedError
        await self.set_request_attrs(self.request, user)
        self.rotate_csrf_token()
        return self.to_response(
            await self.make_api_response(),
            status_code=self.response_status_code,
            headers=self.response_headers(),
            cookies=self.issue_cookies(),
        )

    @abstractmethod
    async def convert_auth_payload(
        self,
        payload: _ObtainTokensT,
    ) -> ObtainTokensPayload:
        """
        Convert your custom payload to the kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports, basically it needs
        ``username`` and ``password`` strings.
        """
        raise NotImplementedError


class CookieRefreshTokensSyncController(
    _BaseCookieTokensSyncController[_SerializerT, _CookieResponseT],
    BaseRefreshTokenController[_SerializerT],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to rotate both token cookies.

    Reads the refresh token from its cookie, validates it,
    loads the user, and sets a brand new pair of cookies.
    There is no request body: the browser sends the cookie on its own,
    which is also why we check CSRF here.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.

    See :class:`~dmr.security.jwt.views.CookieObtainTokensSyncController`
    for the rest of the settings.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the sync cookie refresh controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies=cls.issued_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @sensitive_variables()
    @validate.lazy(validate_spec)
    def post(self) -> HttpResponse:
        """Rotate both cookies on post."""
        return self.refresh()

    def refresh(self) -> HttpResponse:
        """Validate the refresh cookie, load user, and set new cookies."""
        self.check_csrf()
        token = self._decode_and_validate_refresh_token(
            self.get_cookie_token(self.jwt_refresh_cookie),
        )
        user = self.get_user(token)
        self.check_auth(user, token)
        self.set_request_attrs(self.request, user)
        return self.to_response(
            self.make_api_response(),
            status_code=self.response_status_code,
            headers=self.response_headers(),
            cookies=self.issue_cookies(),
        )

    def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch the user this refresh token was issued for."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return get_user_model().objects.get(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    def check_auth(
        self,
        user: AbstractBaseUser,
        token: JWToken,
    ) -> None:
        """Run extra checks on the refreshing user, raise to reject."""
        if not user.is_active:
            raise NotAuthenticatedError


class CookieRefreshTokensAsyncController(
    _BaseCookieTokensAsyncController[_SerializerT, _CookieResponseT],
    BaseRefreshTokenController[_SerializerT],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Async controller to rotate both token cookies.

    Reads the refresh token from its cookie, validates it,
    loads the user, and sets a brand new pair of cookies.
    There is no request body: the browser sends the cookie on its own,
    which is also why we check CSRF here.

    Attributes:
        jwt_user_id_field: User model field matched against ``token.sub``.
            Defaults to ``'pk'``.

    See :class:`~dmr.security.jwt.views.CookieObtainTokensAsyncController`
    for the rest of the settings.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the async cookie refresh controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies=cls.issued_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @sensitive_variables()
    @validate.lazy(validate_spec)
    async def post(self) -> HttpResponse:
        """Rotate both cookies on post."""
        return await self.refresh()

    @sensitive_variables()
    async def refresh(self) -> HttpResponse:
        """Validate the refresh cookie, load user, and set new cookies."""
        self.check_csrf()
        token = self._decode_and_validate_refresh_token(
            self.get_cookie_token(self.jwt_refresh_cookie),
        )
        user = await self.get_user(token)
        await self.check_auth(user, token)
        await self.set_request_attrs(self.request, user)
        return self.to_response(
            await self.make_api_response(),
            status_code=self.response_status_code,
            headers=self.response_headers(),
            cookies=self.issue_cookies(),
        )

    @sensitive_variables()
    async def get_user(self, token: JWToken) -> AbstractBaseUser:
        """Fetch the user this refresh token was issued for."""
        from django.contrib.auth import get_user_model  # noqa: PLC0415

        try:
            return await get_user_model().objects.aget(**{
                self.jwt_user_id_field: token.sub,
            })
        except USER_LOOKUP_ERRORS:
            raise NotAuthenticatedError from None

    @sensitive_variables()
    async def check_auth(
        self,
        user: AbstractBaseUser,
        token: JWToken,
    ) -> None:
        """Run extra checks on the refreshing user, raise to reject."""
        if not user.is_active:
            raise NotAuthenticatedError


class CookieLogoutSyncController(
    _BaseCookieTokensSyncController[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to drop both token cookies.

    Sends both cookies back empty and already expired,
    so the browser drops them right away.
    It is transport-only: a token that leaked before the logout
    stays valid until it expires. Override :meth:`revoke_tokens`
    to also put it into the blocklist,
    see :ref:`blocklisting-tokens`.

    There is no request body, which is why we check CSRF here.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the sync cookie logout controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies=cls.discarded_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @sensitive_variables()
    @validate.lazy(validate_spec)
    def post(self) -> HttpResponse:
        """By default cookies are dropped on post."""
        return self.logout()

    def logout(self) -> HttpResponse:
        """Perform the sync logout routine and drop the token cookies."""
        self.check_csrf()
        self.revoke_tokens()
        return self.to_response(
            self.make_api_response(),
            status_code=self.response_status_code,
            headers=self.response_headers(),
            cookies=self.discard_cookies(),
        )

    def revoke_tokens(self) -> None:
        """
        Hook to invalidate the tokens we are logging out of.

        Does nothing by default, because the blocklist app is optional.
        With it installed, blocklist
        :func:`~dmr.security.jwt.auth.request_jwt` of this request.
        """


class CookieLogoutAsyncController(
    _BaseCookieTokensAsyncController[_SerializerT, _CookieResponseT],
):
    """
    Async controller to drop both token cookies.

    Sends both cookies back empty and already expired,
    so the browser drops them right away.
    It is transport-only: a token that leaked before the logout
    stays valid until it expires. Override :meth:`revoke_tokens`
    to also put it into the blocklist,
    see :ref:`blocklisting-tokens`.

    There is no request body, which is why we check CSRF here.

    .. versionadded:: 0.15.0
    """

    response_status_code: ClassVar[HTTPStatus] = HTTPStatus.NO_CONTENT

    @classmethod
    def validate_spec(cls) -> ValidateAnyCallable:
        """Lazy endpoint spec for the async cookie logout controller."""
        return validate(
            ResponseSpec(
                _COOKIE_RESPONSE_TYPE,
                status_code=cls.response_status_code,
                headers=cls.response_headers_spec(),
                cookies=cls.discarded_cookies_spec(),
            ),
            *cls.csrf_response_specs(),
        )

    @sensitive_variables()
    @validate.lazy(validate_spec)
    async def post(self) -> HttpResponse:
        """By default cookies are dropped on post."""
        return await self.logout()

    async def logout(self) -> HttpResponse:
        """Perform the async logout routine and drop the token cookies."""
        self.check_csrf()
        await self.revoke_tokens()
        return self.to_response(
            await self.make_api_response(),
            status_code=self.response_status_code,
            headers=self.response_headers(),
            cookies=self.discard_cookies(),
        )

    async def revoke_tokens(self) -> None:
        """
        Hook to invalidate the tokens we are logging out of.

        Does nothing by default, because the blocklist app is optional.
        With it installed, blocklist
        :func:`~dmr.security.jwt.auth.request_jwt` of this request.
        """
