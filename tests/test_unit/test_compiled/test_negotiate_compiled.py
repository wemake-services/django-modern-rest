import sys

import pytest


@pytest.mark.parametrize(
    ('accept', 'provided_types', 'best_match'),
    [
        ('text/plain', ['text/plain'], 'text/plain'),
        ('text/plain', ['text/html'], None),
        ('text/*', ['text/html'], 'text/html'),
        ('*/*', ['text/html'], 'text/html'),
        ('', ['text/html'], None),
        ('text/plain;p=test', ['text/plain'], 'text/plain'),
        ('text/plain', ['text/plain;p=test'], None),
        ('text/plain;p=test', ['text/plain;p=test'], 'text/plain;p=test'),
        ('text/plain', ['text/*'], 'text/plain'),
        ('text/html', ['*/*'], 'text/html'),
        (
            'text/plain;q=0.8,text/html',
            ['text/plain', 'text/html'],
            'text/html',
        ),
        (
            'text/plain;q=ab,text/html',
            ['text/plain', 'text/html'],
            'text/plain',
        ),
        ('text/*,text/html', ['text/plain', 'text/html'], 'text/html'),
    ],
)
@pytest.mark.parametrize('compiled', [True, False])
def test_accept_best_match(
    monkeypatch: pytest.MonkeyPatch,
    *,
    accept: str,
    provided_types: list[str],
    best_match: str | None,
    compiled: bool,
) -> None:
    """Ensure that selection of accepted type works correctly."""
    # Our setup, it can be compiled or not:
    monkeypatch.setenv('DMR_USE_COMPILED', str(int(compiled)))
    sys.modules.pop('dmr.envs', None)
    sys.modules.pop('dmr.compiled', None)

    from dmr.compiled import accepted_type  # noqa: PLC0415
    from dmr.envs import USE_COMPILED  # noqa: PLC0415

    assert USE_COMPILED is compiled
    if compiled:
        assert '_pure' not in accepted_type.__module__, (USE_COMPILED, compiled)
    else:
        assert '_pure' in accepted_type.__module__, (USE_COMPILED, compiled)

    # The function itself:
    assert accepted_type(accept, provided_types) == best_match
