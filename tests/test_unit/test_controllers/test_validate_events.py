from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.streaming import StreamingController
from dmr.streaming.jsonl import JsonLinesController
from dmr.streaming.sse import SSEController

_STREAMING_ONLY: Final = 'can only be used with streaming controllers'


@pytest.mark.parametrize('validate_events', [True, False])
def test_modify_non_streaming(*, validate_events: bool) -> None:
    """Ensure that ``@modify`` can't set ``validate_events`` for regular."""
    with pytest.raises(EndpointMetadataError, match=_STREAMING_ONLY):

        class _Controller(Controller[PydanticSerializer]):
            @modify(validate_events=validate_events)
            def get(self) -> str:
                raise NotImplementedError


@pytest.mark.parametrize('validate_events', [True, False])
def test_validate_non_streaming(*, validate_events: bool) -> None:
    """Ensure that ``@validate`` can't set ``validate_events`` for regular."""
    with pytest.raises(EndpointMetadataError, match=_STREAMING_ONLY):

        class _Controller(Controller[PydanticSerializer]):
            @validate(
                ResponseSpec(str, status_code=HTTPStatus.OK),
                validate_events=validate_events,
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError


@pytest.mark.parametrize('is_enabled', [True, False])
def test_controller_non_streaming(*, is_enabled: bool) -> None:
    """Ensure that regular controllers can't set ``validate_events``."""
    with pytest.raises(EndpointMetadataError, match=_STREAMING_ONLY):

        class _Controller(Controller[PydanticSerializer]):
            validate_events = is_enabled

            def get(self) -> str:
                raise NotImplementedError


def test_base_controller_non_streaming() -> None:
    """Ensure that ``validate_events`` from a base controller is rejected."""

    class _BaseController(Controller[PydanticSerializer]):
        validate_events = True

    with pytest.raises(EndpointMetadataError, match=_STREAMING_ONLY):

        class _Controller(_BaseController):
            def get(self) -> str:
                raise NotImplementedError


def test_settings_non_streaming(settings: LazySettings) -> None:
    """Ensure that settings can set ``validate_events`` for all controllers."""
    settings.DMR_SETTINGS = {Settings.validate_events: False}

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.validate_events is False


@pytest.mark.parametrize('base', [SSEController, JsonLinesController])
@pytest.mark.parametrize('is_enabled', [True, False])
def test_streaming_controllers(
    *,
    base: type[StreamingController[BaseSerializer]],
    is_enabled: bool,
) -> None:
    """Ensure that streaming controllers can set ``validate_events``."""

    class _Controller(base[PydanticSerializer]):  # type: ignore[valid-type, misc]
        validate_events = not is_enabled

        async def get(self) -> AsyncIterator[str]:
            raise NotImplementedError

        @modify(validate_events=is_enabled)
        async def post(self) -> AsyncIterator[str]:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints  # pyrefly: ignore[missing-attribute]
    assert endpoints['GET'].metadata.validate_events is not is_enabled
    assert endpoints['POST'].metadata.validate_events is is_enabled
