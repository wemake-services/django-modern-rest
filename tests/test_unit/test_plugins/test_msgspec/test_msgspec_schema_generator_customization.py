from typing import Any

import pytest

pytest.importorskip('msgspec')

from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator


class _Unsupported:
    """A plain class msgspec cannot generate a schema for natively."""

    attr: int


def _unsupported_schema_hook(cls: type) -> dict[str, Any]:
    """Provide a schema for `_Unsupported`, the only extra type known."""
    if cls is _Unsupported:
        return {'type': 'object', 'title': 'Unsupported'}
    raise NotImplementedError(f'Unsupported type: {cls!r}')  # pragma: no cover


def test_default_hook_raises_for_unsupported() -> None:
    """Without a hook, msgspec cannot handle arbitrary classes."""
    with pytest.raises(TypeError, match='schema_hook'):
        MsgspecSchemaGenerator.get_schema(
            _Unsupported,
            ref_template='#/components/schemas/',
        )


def test_custom_hook_handles_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subclass can override `schema_hook` to support extra types."""
    monkeypatch.setattr(
        MsgspecSchemaGenerator,
        'schema_hook',
        _unsupported_schema_hook,
    )

    schema, _ = MsgspecSchemaGenerator.get_schema(
        _Unsupported,
        ref_template='#/components/schemas/',
    )

    assert schema['title'] == 'Unsupported'
