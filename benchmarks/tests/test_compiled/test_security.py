from __future__ import annotations

from base64 import b64encode
from typing import TYPE_CHECKING, Final

import pytest
from pytest_codspeed import BenchmarkFixture

if TYPE_CHECKING:
    from conftest import CleanModules


_CASES: Final = (
    # basic cases
    ('admin', 'pass', 'Basic ', 'Basic YWRtaW46cGFzcw=='),
    ('user', '1234', 'Basic ', 'Basic dXNlcjoxMjM0'),
    # no prefix
    ('admin', 'pass', '', 'YWRtaW46cGFzcw=='),
    # custom prefix
    ('admin', 'pass', 'Bearer ', 'Bearer YWRtaW46cGFzcw=='),
    # empty username / password
    ('', '', 'Basic ', 'Basic Og=='),  # ":"
    ('user', '', 'Basic ', 'Basic dXNlcjo='),  # "user:"
    ('', 'pass', 'Basic ', 'Basic OnBhc3M='),  # ":pass"
    # special characters
    ('user', 'p@ss:word', 'Basic ', 'Basic dXNlcjpwQHNzOndvcmQ='),
    ('üser', 'päss', 'Basic ', 'Basic w7xzZXI6cMOkc3M='),
    # whitespace
    (' user ', ' pass ', 'Basic ', 'Basic IHVzZXIgOiBwYXNzIA=='),
    # long values
    *tuple(
        (
            'a' * n,
            'b' * n,
            'Basic ',
            'Basic ' + b64encode(f'{"a" * n}:{"b" * n}'.encode()).decode(),
        )
        for n in range(10, 101, 10)
    ),
)


def test_basic_auth_compiled(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: CleanModules,
) -> None:
    """Test compiled version of the basic_auth."""

    monkeypatch.setenv('DMR_USE_COMPILED', '1')

    with clean_modules():
        from dmr._compiled import security  # noqa: PLC0415, PLC2701

        assert security.__file__.endswith('.so')

        from dmr.compiled import basic_auth  # noqa: PLC0415

        assert '_pure' not in basic_auth.__module__

        @benchmark
        def factory() -> None:
            for username, password, prefix, expected in _CASES:
                assert basic_auth(username, password, prefix=prefix) == expected


def test_basic_auth_raw(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: CleanModules,
) -> None:
    """Test raw version of the basic_auth."""

    monkeypatch.setenv('DMR_USE_COMPILED', '0')

    with clean_modules():
        from dmr.compiled import basic_auth  # noqa: PLC0415

        assert '_pure' in basic_auth.__module__

        @benchmark
        def factory() -> None:
            for username, password, prefix, expected in _CASES:
                assert basic_auth(username, password, prefix=prefix) == expected
