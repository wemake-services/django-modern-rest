from http import HTTPStatus
from typing import Any, Final

import pytest
from django.conf import LazySettings

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import Settings
from dmr.throttling import Rate, SyncThrottle

# We don't care about this warning here.
_SYNC_THROTTLE: Final = SyncThrottle(
    1,
    Rate.second,
)


@pytest.mark.parametrize('throttling_def', [None, [], ()])
def test_empty_throttle_disables_controller(
    *,
    throttling_def: Any,
) -> None:
    """Empty `throttle` on the endpoint disables all."""

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        throttling = [_SYNC_THROTTLE]

        @modify(throttling=throttling_def)  # type: ignore[untyped-decorator]
        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.throttling is None
    assert HTTPStatus.TOO_MANY_REQUESTS not in metadata.responses


@pytest.mark.parametrize('throttling_def', [None, [], ()])
def test_empty_throttle_disables_settings(
    settings: LazySettings,
    *,
    throttling_def: Any,
) -> None:
    """Empty `throttling` on the endpoint disables all."""
    settings.DMR_SETTINGS = {Settings.throttling: [_SYNC_THROTTLE]}

    class _DisabledEndpointController(Controller[PydanticSerializer]):
        throttling = throttling_def

        def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledEndpointController.api_endpoints['GET'].metadata

    assert metadata.throttling is None
    assert HTTPStatus.TOO_MANY_REQUESTS not in metadata.responses
