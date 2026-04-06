from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_codspeed import BenchmarkFixture

from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.renderers import Renderer
from dmr.streaming.sse import SSEvent
from dmr.streaming.sse.renderer import SSERenderer
from dmr.streaming.validation import StreamingValidator

if TYPE_CHECKING:
    from conftest import CleanModules

EVENTS_N = 10_000
SHORT_EVENT_LEN = 1_000
MID_EVENT_LEN = 10_000
LARGE_EVENT_LEN = 100_000

events = (
    *[SSEvent(b'a', serialize=False) for _ in range(EVENTS_N)],
    SSEvent(
        1,
        event='first',
        id=100,
        retry=5,
        comment='multi\nline\n',
    ),
    SSEvent(b'third', retry=1, id=10, serialize=False),
    SSEvent({'user': 1}),
    SSEvent(comment='ping'),
    SSEvent(event='pong'),
    SSEvent({'newline in key\n': 1}),
    SSEvent(['list item with\nnewline']),
    SSEvent('new\r\nline in str'),
    SSEvent(b'new\r\nline in bytes', serialize=False),
    SSEvent(b'a' * SHORT_EVENT_LEN, serialize=False),
    SSEvent(b'a' * MID_EVENT_LEN, serialize=False),
    SSEvent(b'a' * LARGE_EVENT_LEN, serialize=False),
)


EXPECTED = (
    b''.join(b'data: a\r\n\r\n' for _ in range(EVENTS_N)) + b': multi\r\n'
    b': line\r\n'
    b': \r\n'
    b'id: 100\r\n'
    b'event: first\r\n'
    b'data: 1\r\n'
    b'retry: 5\r\n'
    b'\r\n'
    b'id: 10\r\n'
    b'data: third\r\n'
    b'retry: 1\r\n'
    b'\r\n'
    b'data: {"user":1}\r\n'
    b'\r\n'
    b': ping\r\n'
    b'\r\n'
    b'event: pong\r\n'
    b'\r\n'
    b'data: {"newline in key\\n":1}\r\n'  # noqa: WPS342
    b'\r\n'
    b'data: ["list item with\\nnewline"]\r\n'  # noqa: WPS342
    b'\r\n'
    b'data: "new\\r\\nline in str"\r\n'  # noqa: WPS342
    b'\r\n'
    b'data: new\r\n'
    b'data: line in bytes\r\n'
    b'\r\n'
    b'data: ' + b'a' * SHORT_EVENT_LEN + b'\r\n'
    b'\r\n'
    b'data: ' + b'a' * MID_EVENT_LEN + b'\r\n'
    b'\r\n'
    b'data: ' + b'a' * LARGE_EVENT_LEN + b'\r\n'
    b'\r\n'
)

RENDERERS = (
    SSERenderer(PydanticFastSerializer, Renderer(), StreamingValidator),
)


@pytest.mark.parametrize('renderer', RENDERERS)
def test_render_compiled(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: CleanModules,
    renderer: SSERenderer,
) -> None:
    """Test compiled version of the negotiation protocol."""

    monkeypatch.setenv('DMR_USE_COMPILED', '1')

    with clean_modules():
        from dmr._compiled import sse  # noqa: PLC0415, PLC2701

        assert sse.__file__.endswith('.so')

        from dmr.compiled import render_event_impl  # noqa: PLC0415

        assert '_pure' not in render_event_impl.__module__

        @benchmark
        def factory() -> None:
            collected = bytearray()
            for event in events:
                collected.extend(renderer.render(event, lambda x: None))

            assert bytes(collected) == EXPECTED


@pytest.mark.parametrize('renderer', RENDERERS)
def test_render_raw(
    benchmark: BenchmarkFixture,
    monkeypatch: pytest.MonkeyPatch,
    clean_modules: CleanModules,
    renderer: SSERenderer,
) -> None:
    """Test raw version of the negotiation protocol."""

    monkeypatch.setenv('DMR_USE_COMPILED', '0')

    with clean_modules():
        from dmr.compiled import render_event_impl  # noqa: PLC0415

        assert '_pure' in render_event_impl.__module__

        @benchmark
        def factory() -> None:
            collected = bytearray()
            for event in events:
                collected.extend(renderer.render(event, lambda x: None))

            assert bytes(collected) == EXPECTED
