# A lot of code here is inspired by / taken from `litestar` project
# under a MIT license. See:
# https://github.com/litestar-org/litestar/blob/main/litestar/security/jwt/token.py

# Original license:
# https://github.com/litestar-org/litestar/blob/main/LICENSE

# The MIT License (MIT)

# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 Litestar Org.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime as dt
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Self

import jwt
from jwt.types import Options

from dmr.exceptions import InternalServerError, NotAuthenticatedError


@dataclass(frozen=True, slots=True)
class JWToken:  # noqa: WPS214
    """
    JWT Token DTO.

    Attributes:
        sub: Subject - usually a unique identifier
            of the user or equivalent entity.
        exp: Expiration - datetime for token expiration.
        iat: Issued at - should always be current now.
        iss: Issuer - optional unique identifier for the issuer.
        aud: Audience - intended audience(s).
        jti: JWT ID - a unique identifier of the JWT between different issuers.
        extras: Extra fields that were found on the JWT token.

    .. versionchanged:: 0.15.0

        Init-only ``leeway`` argument was removed.
        Time-based claims are now validated in a single place
        for each direction: :meth:`encode` checks that a token
        can be issued, while :meth:`decode` fully relies
        on ``pyjwt`` and its options.

    """

    sub: str
    exp: dt.datetime

    # Optional fields:
    iat: dt.datetime = field(
        default_factory=lambda: _normalize_datetime(
            dt.datetime.now(dt.UTC),
        ),
    )
    iss: str | None = None
    aud: str | Sequence[str] | None = None
    jti: str | None = None
    extras: dict[str, Any] = field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        """Normalizes datetime claims and runs extra validation."""
        if len(self.sub) < 1:
            raise ValueError(
                'sub must be a string with a length greater than 0',
            )

        object.__setattr__(self, 'exp', _normalize_datetime(self.exp))
        object.__setattr__(self, 'iat', _normalize_datetime(self.iat))

    def validate_issued_claims(self) -> None:
        """
        Ensure that this token makes sense to be issued right now.

        Is called by :meth:`encode`, override it to change or to extend
        the checks that we run before signing a token.

        Raises:
            ValueError: If this token cannot be issued right now.

        .. versionadded:: 0.15.0

        """
        now = _normalize_datetime(dt.datetime.now(dt.UTC)).timestamp()
        if self.exp.timestamp() < now:
            raise ValueError('exp value must be a datetime in the future')
        if self.iat.timestamp() > now:
            raise ValueError('iat must be a current or past time')

    def encode(
        self,
        secret: str | bytes,
        algorithm: str,
        headers: dict[str, Any] | None = None,
    ) -> str:
        """
        Encode the token instance into a string.

        Args:
            secret: The secret with which the JWT is encoded.
            algorithm: The algorithm used to encode the JWT.
            headers: Optional headers to include
                in the JWT (e.g., {"kid": "..."}).

        Returns:
            An encoded token string.

        Raises:
            ValueError: If this token cannot be issued right now.
            InternalServerError: If encoding fails.

        .. versionchanged:: 0.15.0

            ``exp`` and ``iat`` are validated here
            via :meth:`validate_issued_claims`,
            previously it was done during the instance creation.

        """
        self.validate_issued_claims()
        try:
            return jwt.encode(
                payload={
                    field_name: field_value
                    for field_name, field_value in asdict(self).items()
                    if field_value is not None
                },
                key=secret,
                algorithm=algorithm,
                headers=headers,
            )
        except (jwt.exceptions.PyJWTError, NotImplementedError):
            raise InternalServerError('Failed to encode token') from None

    @classmethod
    def decode_payload(  # noqa: WPS211
        cls,
        encoded_token: str,
        secret: str,
        algorithms: list[str],
        *,
        leeway: int,
        issuer: str | Sequence[str] | None,
        audience: str | Sequence[str] | None,
        options: Options | None,
    ) -> dict[str, Any]:
        """Decode and verify the JWT and return its payload."""
        return jwt.decode(
            encoded_token,
            key=secret,
            algorithms=algorithms,
            issuer=issuer,
            audience=audience,
            leeway=leeway,
            options=options,
        )

    @classmethod
    def decode(  # noqa: WPS211
        cls,
        encoded_token: str,
        secret: str,
        algorithm: str,
        *,
        leeway: int = 0,  # seconds
        accepted_audiences: str | Sequence[str] | None = None,
        accepted_issuers: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_exp: bool = True,
        verify_iat: bool = True,
        verify_jti: bool = True,
        verify_nbf: bool = True,
        verify_sub: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = True,
    ) -> Self:
        """
        Decode a passed in token string and return a Token instance.

        Args:
            encoded_token: A base64 string containing an encoded JWT.
            secret: The secret with which the JWT is encoded.
            algorithm: The algorithm used to encode the JWT.
            leeway: Number of potential seconds as a clock error
                for expired tokens.
            accepted_audiences: Verify the audience when decoding the token.
            accepted_issuers: Verify the issuer when decoding the token.
            require_claims: Verify that the given claims
                are present in the token.
            verify_exp: Verify that the value of the ``exp`` (*expiration*)
                claim is in the future.
            verify_iat: Verify that ``iat`` (*issued at*)
                claim value is an integer.
            verify_jti: Check that ``jti`` (*JWT ID*) claim is a string.
            verify_nbf: Verify that the value of the ``nbf`` (*not before*)
                claim is in the past.
            verify_sub: Check that ``sub`` (*subject*) claim is a string.
            strict_audience: Verify that the value of the ``aud`` (*audience*)
                claim is a single value, and not a list of values,
                and matches ``audience`` exactly.
                Requires the value passed to the ``audience`` to be a sequence
                of length 1.
            enforce_minimum_key_length: Raise an auth error when
                keys are below minimum recommended length.

        Returns:
            A decoded Token instance.

        Raises:
            NotAuthenticatedError: If the token is invalid.

        See also:
            https://pyjwt.readthedocs.io/en/stable/api.html#jwt.types.Options

        .. versionchanged:: 0.15.0

            Time-based claims are only validated by ``pyjwt``,
            we don't validate them a second time anymore.
            This means that ``leeway``, ``verify_exp``, and ``verify_iat``
            are now respected, and that invalid tokens always
            raise :exc:`dmr.exceptions.NotAuthenticatedError`.

        """
        options = cls._build_options(
            audience=accepted_audiences,
            issuer=accepted_issuers,
            require_claims=require_claims,
            verify_exp=verify_exp,
            verify_iat=verify_iat,
            verify_jti=verify_jti,
            verify_nbf=verify_nbf,
            verify_sub=verify_sub,
            strict_audience=strict_audience,
            enforce_minimum_key_length=enforce_minimum_key_length,
        )

        try:
            payload = cls.decode_payload(
                encoded_token=encoded_token,
                secret=secret,
                algorithms=[algorithm],
                audience=accepted_audiences,
                issuer=accepted_issuers,
                leeway=leeway,
                options=options,
            )
        except jwt.exceptions.InvalidTokenError:
            raise NotAuthenticatedError from None

        # Convert types to match our definition:
        payload['exp'] = cls._decode_datetime_claim(payload, 'exp')
        payload['iat'] = cls._decode_datetime_claim(payload, 'iat')
        cls._require_claim(payload, 'sub')

        extra_fields = payload.keys() - {field.name for field in fields(cls)}
        extras = payload.setdefault('extras', {})
        for key in extra_fields:
            extras[key] = payload.pop(key)

        try:
            return cls(**payload)
        except ValueError:
            # Time-based claims are already checked by `pyjwt` above,
            # everything else that is invalid here is still a bad token.
            raise NotAuthenticatedError from None

    @classmethod
    def _build_options(  # noqa: WPS211
        cls,
        *,
        audience: str | Sequence[str] | None = None,
        issuer: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_exp: bool = True,
        verify_iat: bool = True,
        verify_jti: bool = True,
        verify_nbf: bool = True,
        verify_sub: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = False,
    ) -> Options:
        if strict_audience and not isinstance(audience, str):
            raise ValueError(
                "When using 'strict_audience=True', "
                "'audience' must be a single string",
            )

        options: Options = {
            'strict_aud': strict_audience,
            'verify_aud': bool(audience),
            'verify_iss': bool(issuer),
            'verify_exp': verify_exp,
            'verify_iat': verify_iat,
            'verify_jti': verify_jti,
            'verify_nbf': verify_nbf,
            'verify_sub': verify_sub,
            'enforce_minimum_key_length': enforce_minimum_key_length,
            'require': list(require_claims) if require_claims else [],
        }
        return options

    @classmethod
    def _require_claim(
        cls,
        payload: dict[str, Any],
        claim: str,
    ) -> Any:
        try:
            return payload[claim]
        except KeyError as error:
            raise NotAuthenticatedError from error

    @classmethod
    def _decode_datetime_claim(
        cls,
        payload: dict[str, Any],
        claim: str,
    ) -> dt.datetime:
        claim_value = cls._require_claim(payload, claim)
        try:
            return dt.datetime.fromtimestamp(
                claim_value,
                tz=dt.UTC,
            )
        except (TypeError, ValueError, OSError):
            raise NotAuthenticatedError from None


def _normalize_datetime(datetime: dt.datetime) -> dt.datetime:
    """Convert the given value into UTC and strip microseconds."""
    if datetime.tzinfo is not None:
        datetime = datetime.astimezone(dt.UTC)

    return datetime.replace(microsecond=0)
