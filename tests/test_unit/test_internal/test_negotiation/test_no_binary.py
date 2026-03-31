"""Tests for DMR_NO_BINARY environment variable opt-out mechanism."""

import importlib
import sys
from types import ModuleType

import pytest


def _reload_negotiation_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Force-reload dmr.internal.negotiation in isolation."""
    affected = [
        key
        for key in sys.modules
        if key.startswith('dmr.internal.negotiation')
        or key == 'dmr.internal._negotiation_pure'
    ]
    for key in affected:
        monkeypatch.delitem(sys.modules, key, raising=False)

    mod = importlib.import_module('dmr.internal.negotiation')

    for key in affected:
        monkeypatch.setitem(sys.modules, key, sys.modules.get(key, mod))

    return mod


def test_no_binary_flag_loads_pure_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DMR_NO_BINARY forces the pure-Python implementation."""
    monkeypatch.setenv('DMR_NO_BINARY', '1')

    mod = _reload_negotiation_module(monkeypatch)

    assert callable(mod.negotiate_renderer)
    assert callable(mod.media_by_precedence)
    assert callable(mod.response_validation_negotiator)
    assert mod.ConditionalType is not None


def test_no_binary_unset_uses_normal_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without DMR_NO_BINARY the default import path is used."""
    monkeypatch.delenv('DMR_NO_BINARY', raising=False)

    mod = _reload_negotiation_module(monkeypatch)

    assert callable(mod.negotiate_renderer)
    assert callable(mod.media_by_precedence)
    assert callable(mod.response_validation_negotiator)
    assert mod.ConditionalType is not None
