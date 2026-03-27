from collections.abc import AsyncIterator
from typing import Any

import pytest
from django.conf import LazySettings

from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import Settings
from dmr.streaming.sse import SSEController
from dmr.streaming.sse.renderer import SSERenderer


def test_single_streaming_renderer(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    """Ensure that streaming renderer can't be the only one."""
    settings.DMR_SETTINGS = {
        Settings.renderers: [SSERenderer(PydanticSerializer, JsonRenderer())],
    }

    with pytest.raises(
        EndpointMetadataError,
        match='At least one non-stream renderer is required',
    ):

        class _ClassBasedSSE(SSEController[PydanticSerializer]):
            async def get(self) -> AsyncIterator[Any]:
                raise NotImplementedError
