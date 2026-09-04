import datetime as dt
import decimal
import json
import secrets
import uuid
from typing import Any, Final

import jwt
import pytest
from typing_extensions import override

from dmr.internal.json import NativeJson, json_dump_bytes
from dmr.internal.jwt import dmr_jwt
from dmr.security.jwt import JWToken

try:
    import msgspec
except ImportError:  # pragma: no cover
    _has_msgspec = False
else:
    del msgspec  # noqa: WPS420
    _has_msgspec = True

#: Parity between the two backends can only be compared with both of them.
_msgspec_only: Final = pytest.mark.skipif(
    not _has_msgspec,
    reason='msgspec is not installed',
)

_ALGORITHMS: Final = ('HS256', 'HS384', 'HS512')

#: Values that both json backends encode in exactly the same way.
_MATCHING_VALUES: Final = (
    dt.date.fromisoformat('2026-09-04'),
    dt.time.fromisoformat('12:30:45'),
    dt.datetime.fromisoformat('2026-09-04T12:30:45'),
    uuid.UUID('12345678-1234-5678-1234-567812345678'),
    decimal.Decimal('1.5'),
)

#: Values that the two json backends encode differently.
_DIVERGING_VALUES: Final = (
    dt.datetime.fromisoformat('2026-09-04T12:30:45.123456+00:00'),
    dt.timedelta(minutes=1),
)


def _make_payload() -> dict[str, Any]:
    now = dt.datetime.now(dt.UTC)
    return {
        'sub': secrets.token_hex(),
        'iat': int(now.timestamp()),
        'exp': int((now + dt.timedelta(minutes=1)).timestamp()),
        'iss': 'django-modern-rest',
        'scopes': ['read', 'write'],
    }


@pytest.fixture
def _native_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the json backend we use when ``msgspec`` is missing."""
    monkeypatch.setattr('dmr.internal.jwt.json_dump_bytes', NativeJson.dumps)
    monkeypatch.setattr('dmr.internal.jwt.json_loads', NativeJson.loads)


@pytest.mark.parametrize('algorithm', _ALGORITHMS)
def test_encode_matches_pyjwt(algorithm: str) -> None:
    """Ensures that we produce byte-identical tokens to ``pyjwt``."""
    secret = secrets.token_hex()
    payload = _make_payload()

    assert dmr_jwt.encode(payload, secret, algorithm=algorithm) == jwt.encode(
        payload,
        secret,
        algorithm=algorithm,
    )


@pytest.mark.usefixtures('_native_backend')
@pytest.mark.parametrize('algorithm', _ALGORITHMS)
def test_native_encode_matches_pyjwt(algorithm: str) -> None:
    """Ensures the same for the backend used without ``msgspec``."""
    secret = secrets.token_hex()
    payload = _make_payload()

    assert dmr_jwt.encode(payload, secret, algorithm=algorithm) == jwt.encode(
        payload,
        secret,
        algorithm=algorithm,
    )


@pytest.mark.parametrize('algorithm', _ALGORITHMS)
def test_cross_decode(algorithm: str) -> None:
    """Ensures that both implementations read each other's tokens."""
    secret = secrets.token_hex()
    payload = _make_payload()
    ours = dmr_jwt.encode(payload, secret, algorithm=algorithm)
    theirs = jwt.encode(payload, secret, algorithm=algorithm)

    assert dmr_jwt.decode(theirs, secret, algorithms=[algorithm]) == payload
    assert jwt.decode(ours, secret, algorithms=[algorithm]) == payload


def test_jwtoken_roundtrip_with_extras() -> None:
    """Ensures that ``JWToken`` round-trips json-native ``extras``."""
    secret = secrets.token_hex()
    extras = {'email': 'test@example.com', 'roles': ['admin'], 'age': 30}
    token = JWToken(
        sub=secrets.token_hex(),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=1),
        extras=extras,
    )

    decoded = JWToken.decode(
        token.encode(secret=secret, algorithm='HS256'),
        secret=secret,
        algorithm='HS256',
    )

    assert decoded.extras == extras


def test_encode_payload_honours_json_encoder() -> None:
    """Ensures a custom ``json_encoder`` falls back to ``pyjwt``."""

    class _SetEncoder(json.JSONEncoder):
        @override
        def default(self, o: Any) -> Any:  # noqa: WPS111
            return sorted(o)

    assert (
        dmr_jwt._encode_payload({'a': {2, 1}}, json_encoder=_SetEncoder)
        == b'{"a":[1,2]}'
    )


@pytest.mark.parametrize('raw_payload', [b'{invalid', b'123'])
def test_decode_payload_errors(raw_payload: bytes) -> None:
    """Ensures that a broken payload raises ``DecodeError``."""
    secret = secrets.token_hex()
    token = jwt.PyJWS().encode(raw_payload, secret, algorithm='HS256')

    with pytest.raises(
        jwt.exceptions.DecodeError,
        match='Invalid payload string',
    ):
        dmr_jwt.decode(token, secret, algorithms=['HS256'])


@pytest.mark.usefixtures('_native_backend')
@pytest.mark.parametrize('raw_payload', [b'{invalid', b'123'])
def test_native_decode_payload_errors(raw_payload: bytes) -> None:
    """Ensures the same for the backend used without ``msgspec``."""
    secret = secrets.token_hex()
    token = jwt.PyJWS().encode(raw_payload, secret, algorithm='HS256')

    with pytest.raises(
        jwt.exceptions.DecodeError,
        match='Invalid payload string',
    ):
        dmr_jwt.decode(token, secret, algorithms=['HS256'])


@pytest.mark.parametrize('claim', _MATCHING_VALUES)
def test_backends_agree_on_extended_types(claim: Any) -> None:
    """Ensures both backends encode these extra types identically."""
    assert NativeJson.dumps({'v': claim}) == json_dump_bytes({'v': claim})


@_msgspec_only
@pytest.mark.parametrize('claim', _DIVERGING_VALUES)
def test_backends_diverge_on_extended_types(claim: Any) -> None:
    """Documents that these types are backend dependent in ``extras``."""
    assert NativeJson.dumps({'v': claim}) != json_dump_bytes({'v': claim})


@_msgspec_only
@pytest.mark.parametrize('claim', [{1, 2}, b'ab'])
def test_native_rejects_msgspec_only_types(claim: Any) -> None:
    """Documents that ``set`` and ``bytes`` only work with ``msgspec``."""
    assert json_dump_bytes({'v': claim})

    with pytest.raises(TypeError):
        NativeJson.dumps({'v': claim})


@_msgspec_only
def test_backends_diverge_on_nan() -> None:
    """Documents that ``NaN`` is not portable between the backends."""
    assert json_dump_bytes({'v': float('nan')}) == b'{"v":null}'
    assert NativeJson.dumps({'v': float('nan')}) == b'{"v":NaN}'
