from collections.abc import AsyncIterator
from typing import Any

from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import default_renderer
from dmr.streaming.sse import SSEController, SSEvent


class _ExplicitRenderers(SSEController[PydanticSerializer]):
    renderers = (JsonRenderer(ContentType.json_problem_details),)

    async def get(self) -> AsyncIterator[SSEvent[Any]]:
        raise NotImplementedError


class _DefaultRenderers(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[SSEvent[Any]]:
        raise NotImplementedError


def test_streaming_explicit_renderers() -> None:
    """Ensure that explicit renderers are used with streaming ones."""
    renderers = _ExplicitRenderers.api_endpoints['GET'].metadata.renderers

    assert set(renderers) == {
        ContentType.event_stream,
        ContentType.json_problem_details,
    }


def test_streaming_default_renderers() -> None:
    """Ensure that settings renderers are used when nothing is set."""
    renderers = _DefaultRenderers.api_endpoints['GET'].metadata.renderers

    assert set(renderers) == {
        ContentType.event_stream,
        default_renderer.content_type,
    }
