# A lot of code here is inspired by / taken from `litestar` project
# under a MIT license. See:
# https://github.com/litestar-org/litestar/blob/main/tests/unit/test_security/test_jwt/test_token.py
# https://github.com/litestar-org/litestar/blob/main/LICENSE

import dataclasses
import datetime as dt
import secrets
from typing import Any, TypedDict

import jwt
import pytest
from faker import Faker

from dmr.exceptions import InternalServerError, NotAuthenticatedError
from dmr.security.jwt import JWToken


class _DecodeKwargs(TypedDict, total=False):
    verify_exp: bool
    verify_iat: bool
    verify_sub: bool


@pytest.mark.parametrize('algorithm', ['HS256', 'HS384', 'HS512'])
@pytest.mark.parametrize(
    'token_issuer',
    [None, 'e3d7d10edbbc28bfebd8861d39ae7587acde1e1fcefe2cbbec686d235d68f475'],
)
@pytest.mark.parametrize(
    'token_audience',
    [None, '627224198b4245ed91cf8353e4ccdf1650728c7ee92748f55fe1e9a9c4d961df'],
)
@pytest.mark.parametrize(
    'token_unique_jwt_id',
    [None, '10f5c6967783ddd6bb0c4e8262d7097caeae64705e45f83275e3c32eee5d30f2'],
)
@pytest.mark.parametrize('token_extras', [None, {'email': 'test@example.com'}])
def test_token_roundtrip(
    *,
    algorithm: str,
    token_issuer: str | None,
    token_audience: str | None,
    token_unique_jwt_id: str | None,
    token_extras: dict[str, Any] | None,
) -> None:
    """Ensures that token encode/decode roundtrips with different params."""
    token_secret = secrets.token_hex()
    token = JWToken(
        sub=secrets.token_hex(),
        exp=(dt.datetime.now(dt.UTC) + dt.timedelta(minutes=1)),
        aud=token_audience,
        iss=token_issuer,
        jti=token_unique_jwt_id,
        extras=token_extras or {},
    )
    encoded_token = token.encode(secret=token_secret, algorithm=algorithm)
    decoded_token = token.decode(
        encoded_token=encoded_token,
        secret=token_secret,
        algorithm=algorithm,
    )
    assert dataclasses.asdict(token) == dataclasses.asdict(decoded_token)


def test_empty_token() -> None:
    """Ensures that we can't create an empty token."""
    exp = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
    with pytest.raises(ValueError, match='a length greater than 0'):
        JWToken('', exp)


@pytest.mark.parametrize(
    'exp',
    [
        dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
        # datetime with no tz is required to test normalization:
        dt.datetime.now() - dt.timedelta(seconds=1),  # noqa: DTZ005
    ],
)
def test_exp_in_the_past(exp: dt.datetime) -> None:
    """Ensures that we can't create an exp date in the past."""
    with pytest.raises(ValueError, match='datetime in the future'):
        JWToken('a', exp)


def test_iat_in_the_past() -> None:
    """Ensures that we can't create an iat date in the future."""
    exp = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
    with pytest.raises(ValueError, match='current or past time'):
        JWToken('a', exp, iat=exp)


def test_extra_fields(faker: Faker) -> None:
    """Ensures that we can have extra fields on tokens."""
    raw_token = {
        'sub': secrets.token_hex(),
        'iat': dt.datetime.now(dt.UTC),
        'duo': faker.name(),
        'email': faker.email(),
        'exp': (dt.datetime.now(dt.UTC) + dt.timedelta(seconds=10)),
    }
    token_secret = secrets.token_hex()
    encoded_token = jwt.encode(raw_token, key=token_secret, algorithm='HS256')

    token = JWToken.decode(
        encoded_token,
        secret=token_secret,
        algorithm='HS256',
    )

    assert token.extras == {
        'duo': raw_token['duo'],
        'email': raw_token['email'],
    }


def test_strict_audience_validation() -> None:
    """Ensures that strict_audience validates correctly."""
    with pytest.raises(ValueError, match='a single string'):
        JWToken.decode(
            'whatever',
            secret='whatever',  # noqa: S106
            algorithm='HS256',
            accepted_audiences=['multiple', 'values'],
            strict_audience=True,
        )


def test_strict_audience_single_value() -> None:
    """Ensures that strict_audience validates correctly."""
    secret = secrets.token_hex()
    audience = 'foo'
    encoded = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub='foo',
        aud=audience,
    ).encode(secret, 'HS256')

    token = JWToken.decode(
        encoded,
        secret=secret,
        algorithm='HS256',
        accepted_audiences=audience,
        strict_audience=True,
    )

    assert token.aud == audience


@pytest.mark.parametrize(
    ('algorithm', 'secret'),
    [
        (
            'nope',
            '1',
        ),
        (
            '',
            '',
        ),
        (
            '',
            '1',
        ),
    ],
)
def test_encode_validation(
    *,
    algorithm: str,
    secret: str,
) -> None:
    """Ensures that incorrect combination of algorithm and secret raises."""
    with pytest.raises(InternalServerError):
        JWToken(
            sub='123',
            exp=(dt.datetime.now(dt.UTC) + dt.timedelta(seconds=10)),
        ).encode(algorithm=algorithm, secret=secret)


@pytest.mark.parametrize('issuer', [None, 'text', ['list', 'of', 'values']])
def test_token_issuer(issuer: str | list[str] | None) -> None:
    """Ensure that issue validation works."""
    iss = issuer[0] if isinstance(issuer, list) else issuer
    secret = secrets.token_hex()
    encoded = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub='foo',
        iss=iss,
    ).encode(secret, 'HS256')

    token = JWToken.decode(
        encoded,
        secret=secret,
        algorithm='HS256',
        accepted_issuers=issuer,
    )

    assert token.iss == iss


def test_token_encode_includes_custom_headers() -> None:
    """Ensure that custom headers can be provided and work."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub='whatever',
    )
    custom_headers = {'kid': 'key-id'}
    encoded = token.encode(
        secret=secrets.token_hex(),
        algorithm='HS256',
        headers=custom_headers,
    )
    header = jwt.get_unverified_header(encoded)

    assert 'alg' in header
    assert header['alg'] == 'HS256'
    assert 'kid' in header
    assert header['kid'] == custom_headers['kid']


def test_verify_nbf_is_independent_from_exp() -> None:
    """Ensure nbf validation remains enabled independently from exp."""
    secret = secrets.token_hex()
    encoded = jwt.encode(
        {
            'sub': 'foo',
            'iat': dt.datetime.now(dt.UTC),
            'exp': dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            'nbf': dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5),
        },
        key=secret,
        algorithm='HS256',
    )

    with pytest.raises(NotAuthenticatedError):
        JWToken.decode(
            encoded,
            secret=secret,
            algorithm='HS256',
            verify_exp=False,
            verify_nbf=True,
        )


def test_verify_nbf_can_be_disabled_independently() -> None:
    """Ensure nbf validation can be disabled without affecting exp."""
    secret = secrets.token_hex()
    not_before = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5)
    raw_token = {
        'sub': 'foo',
        'iat': dt.datetime.now(dt.UTC),
        'exp': dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        'nbf': not_before,
    }
    encoded = jwt.encode(raw_token, key=secret, algorithm='HS256')

    token = JWToken.decode(
        encoded,
        secret=secret,
        algorithm='HS256',
        verify_exp=True,
        verify_nbf=False,
    )

    assert token.extras['nbf'] == int(not_before.timestamp())


@pytest.mark.parametrize(
    ('raw_token_data', 'decode_kwargs'),
    [
        (
            {
                'sub': 'foo',
                'iat': dt.datetime.now(dt.UTC),
            },
            _DecodeKwargs(verify_exp=False),
        ),
        (
            {
                'sub': 'foo',
                'exp': dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            },
            _DecodeKwargs(verify_iat=False),
        ),
        (
            {
                'exp': dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
                'iat': dt.datetime.now(dt.UTC),
            },
            _DecodeKwargs(verify_sub=False),
        ),
    ],
)
def test_missing_required_claims_raise_auth_error(
    *,
    raw_token_data: dict[str, Any],
    decode_kwargs: _DecodeKwargs,
) -> None:
    """Ensure missing required claims still fail as auth errors."""
    secret = secrets.token_hex()
    encoded = jwt.encode(raw_token_data, key=secret, algorithm='HS256')

    with pytest.raises(NotAuthenticatedError):
        JWToken.decode(
            encoded,
            secret=secret,
            algorithm='HS256',
            **decode_kwargs,
        )


def test_invalid_datetime_claim_raises_auth_error() -> None:
    """Ensure malformed datetime claims fail as auth errors."""
    secret = secrets.token_hex()
    encoded = jwt.encode(
        {
            'sub': 'foo',
            'exp': 'not-a-timestamp',
            'iat': dt.datetime.now(dt.UTC),
        },
        key=secret,
        algorithm='HS256',
    )

    with pytest.raises(NotAuthenticatedError):
        JWToken.decode(
            encoded,
            secret=secret,
            algorithm='HS256',
            verify_exp=False,
        )
