from __future__ import annotations

import secrets
import sys
import time
from typing import TYPE_CHECKING, Any, Final

from pytest_codspeed import BenchmarkFixture

if TYPE_CHECKING:
    from conftest import CleanModules

#: Modules to reimport when switching the json backend.
_JWT_MODULES: Final = frozenset((
    'msgspec',
    'dmr.internal.json',
    'dmr.internal.jwt',
))

_ALGORITHM: Final = 'HS256'
_SECRET: Final = secrets.token_hex()


def _make_payload() -> dict[str, Any]:
    now = int(time.time())
    return {
        'sub': '1234567890',
        'iat': now,
        'exp': now + 3600,
        'iss': 'django-modern-rest',
        'aud': 'web',
        'jti': secrets.token_hex(16),
        'scopes': ['read', 'write'],
    }


def test_jwt_encode_msgspec(benchmark: BenchmarkFixture) -> None:
    """Test encoding with the `msgspec` json backend."""
    from dmr.internal.jwt import dmr_jwt  # noqa: PLC0415

    payload = _make_payload()

    @benchmark
    def factory() -> None:
        dmr_jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def test_jwt_encode_native(
    benchmark: BenchmarkFixture,
    clean_modules: CleanModules,
) -> None:
    """Test encoding without `msgspec` installed."""
    with clean_modules(_JWT_MODULES):
        sys.modules['msgspec'] = None  # type: ignore[assignment]

        from dmr.internal.jwt import dmr_jwt  # noqa: PLC0415

        payload = _make_payload()

        @benchmark
        def factory() -> None:
            dmr_jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def test_jwt_decode_msgspec(benchmark: BenchmarkFixture) -> None:
    """Test decoding with the `msgspec` json backend."""
    from dmr.internal.jwt import dmr_jwt  # noqa: PLC0415

    token = dmr_jwt.encode(_make_payload(), _SECRET, algorithm=_ALGORITHM)

    @benchmark
    def factory() -> None:
        dmr_jwt.decode(
            token,
            _SECRET,
            algorithms=[_ALGORITHM],
            audience='web',
            issuer='django-modern-rest',
        )


def test_jwt_decode_native(
    benchmark: BenchmarkFixture,
    clean_modules: CleanModules,
) -> None:
    """Test decoding without `msgspec` installed."""
    with clean_modules(_JWT_MODULES):
        sys.modules['msgspec'] = None  # type: ignore[assignment]

        from dmr.internal.jwt import dmr_jwt  # noqa: PLC0415

        token = dmr_jwt.encode(_make_payload(), _SECRET, algorithm=_ALGORITHM)

        @benchmark
        def factory() -> None:
            dmr_jwt.decode(
                token,
                _SECRET,
                algorithms=[_ALGORITHM],
                audience='web',
                issuer='django-modern-rest',
            )
