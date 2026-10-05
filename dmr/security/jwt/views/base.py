import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any, ClassVar, Literal, TypeAlias

from django.conf import settings
from django.views.decorators.debug import sensitive_variables
from typing_extensions import TypedDict, TypeVar

from dmr import Controller
from dmr.exceptions import InternalServerError, NotAuthenticatedError
from dmr.security.jwt.token import JWToken, JWTokenError
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)

_TokenType: TypeAlias = Literal['access', 'refresh']


class ObtainTokensPayload(TypedDict):
    """
    Payload for default version of a jwt request body.

    Is also used as kwargs for :func:`django.contrib.auth.authenticate`.
    """

    username: str
    password: str


class BaseTokenSettings:
    """Collection of jwt settings that can be applied to any jwt controller."""

    jwt_audiences: ClassVar[str | Sequence[str] | None] = None
    jwt_issuer: ClassVar[str | None] = None
    jwt_algorithm: ClassVar[str] = 'HS256'
    jwt_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=1)
    jwt_secret: ClassVar[str | None] = None
    jwt_token_cls: ClassVar[type[JWToken]] = JWToken


class BaseObtainTokensSettings(BaseTokenSettings):
    """Settings that can be applied to controllers with refresh tokens."""

    jwt_refresh_expiration: ClassVar[dt.timedelta] = dt.timedelta(days=10)


class BaseTokenController(
    BaseObtainTokensSettings,
    Controller[_SerializerT],
):
    """Base for every controller that issues jwt tokens."""

    @sensitive_variables()
    def create_jwt_token(  # noqa: WPS211
        self,
        *,
        # Most frequent:
        expiration: dt.datetime | None = None,
        token_type: _TokenType | None = None,
        # Less frequent:
        subject: str | None = None,
        issuer: str | None = None,
        audiences: str | Sequence[str] | None = None,
        jwt_id: str | None = None,
        secret: str | None = None,
        algorithm: str | None = None,
        token_headers: dict[str, Any] | None = None,
    ) -> str:
        """Create correct jwt token of a given *expiration* and *token_type*."""
        token = self.jwt_token_cls(
            sub=subject or str(self.request.user.pk),
            exp=expiration or (dt.datetime.now(dt.UTC) + self.jwt_expiration),
            iss=issuer or self.jwt_issuer,
            aud=audiences or self.jwt_audiences,
            jti=jwt_id or self.make_jwt_id(),
            extras={'type': token_type} if token_type else {},
        )
        try:
            return token.encode(
                secret=secret or self.jwt_secret or settings.SECRET_KEY,
                algorithm=algorithm or self.jwt_algorithm,
                headers=token_headers,
            )
        except JWTokenError as exc:
            # Convert the token-layer semantic error at the HTTP boundary.
            raise InternalServerError('Failed to encode token') from exc

    def make_jwt_id(self) -> str | None:
        """Create unique token's jwt id."""
        return uuid.uuid4().hex


class BaseRefreshTokenController(BaseTokenController[_SerializerT]):
    """Base for every controller that accepts a refresh token."""

    jwt_user_id_field: ClassVar[str] = 'pk'

    @sensitive_variables()
    def _decode_and_validate_refresh_token(self, encoded_token: str) -> JWToken:
        token = self.jwt_token_cls.decode(
            encoded_token=encoded_token,
            secret=self.jwt_secret or settings.SECRET_KEY,
            algorithm=self.jwt_algorithm,
            accepted_audiences=self.jwt_audiences,
            accepted_issuers=self.jwt_issuer,
        )
        if token.extras.get('type') != 'refresh':
            raise NotAuthenticatedError
        return token
