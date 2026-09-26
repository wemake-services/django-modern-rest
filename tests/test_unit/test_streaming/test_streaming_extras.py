import dataclasses
from collections.abc import AsyncIterator
from typing import Final, Self, final

import pytest
from django.conf import LazySettings
from typing_extensions import Sentinel, override

from dmr import Controller
from dmr.endpoint import Endpoint, Extras, ModifyEndpoint
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.streaming import Streaming, modify
from dmr.streaming.endpoint import StreamingExtras
from dmr.streaming.sse import SSEController, SSEvent
from dmr.types import EMPTY
from dmr.validation import EndpointMetadataBuilder


async def _events() -> AsyncIterator[SSEvent[int]]:
    yield SSEvent(1)  # pragma: no cover


def test_extras_fallback_from_settings(settings: LazySettings) -> None:
    """Ensures that `EMPTY` `validate_events` falls back to responses."""
    settings.DMR_SETTINGS = {
        Settings.validate_responses: True,
        Settings.validate_events: EMPTY,
    }

    class _Controller(SSEController[PydanticSerializer]):
        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return _events()

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.extras == StreamingExtras(validate_events=True)


def test_extras_configuration_levels() -> None:
    """Ensures that controller defaults are used when extras are not set."""

    class _Controller(SSEController[PydanticSerializer]):
        validate_responses = True
        validate_events = False

        async def get(self) -> AsyncIterator[SSEvent[int]]:
            return _events()

        @modify()
        async def post(self) -> AsyncIterator[SSEvent[int]]:
            return _events()

        @modify(extras=Streaming(validate_events=True))
        async def put(self) -> AsyncIterator[SSEvent[int]]:
            return _events()

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.extras == StreamingExtras(
        validate_events=False,
    )
    assert endpoints['POST'].metadata.extras == StreamingExtras(
        validate_events=False,
    )
    assert endpoints['PUT'].metadata.extras == StreamingExtras(
        validate_events=True,
    )


def test_extras_on_non_streaming_endpoint() -> None:
    """Ensures that extras raise when the endpoint does not support them."""
    with pytest.raises(EndpointMetadataError, match='does not support extras'):

        class _Controller(Controller[PydanticSerializer]):
            @modify(extras=Streaming(validate_events=True))
            def get(self) -> int:
                raise NotImplementedError


def test_validate_events_non_streaming() -> None:
    """Ensures that `validate_events` raises on non-streaming controllers."""
    with pytest.raises(
        EndpointMetadataError,
        match='is not a streaming controller',
    ):

        class _Controller(Controller[PydanticSerializer]):
            validate_events = True

            def get(self) -> int:
                raise NotImplementedError


def test_streaming_extras_non_streaming() -> None:
    """Ensures that `Streaming` checks the controller, not just the endpoint."""

    class _Endpoint(Endpoint):
        extras_cls = Streaming
        __slots__ = ()

    with pytest.raises(EndpointMetadataError, match='non-streaming controller'):

        class _Controller(Controller[PydanticSerializer]):
            endpoint_cls = _Endpoint

            def get(self) -> int:
                raise NotImplementedError


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _CustomExtras(Extras[str]):
    tag: str | Sentinel = EMPTY

    @classmethod
    @override
    def build(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        payload_extras: Self | Sentinel,
        controller_cls: type[Controller[BaseSerializer]],
        builder: EndpointMetadataBuilder,
    ) -> str:
        if isinstance(payload_extras, Sentinel):
            return 'default'
        return builder.merger('tag').not_empty(payload_extras.tag)


_custom_modify: Final = ModifyEndpoint[_CustomExtras]()


class _CustomEndpoint(Endpoint):
    extras_cls = _CustomExtras

    __slots__ = ()


def test_custom_extras() -> None:
    """Ensures that custom endpoints can define their own extras."""

    class _Controller(Controller[PydanticSerializer]):
        endpoint_cls = _CustomEndpoint

        def get(self) -> int:
            raise NotImplementedError

        @_custom_modify(extras=_CustomExtras(tag='custom'))
        def post(self) -> int:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.extras == 'default'
    assert endpoints['POST'].metadata.extras == 'custom'


def test_wrong_extras_type() -> None:
    """Ensures that extras of a wrong type raise."""
    with pytest.raises(
        EndpointMetadataError,
        match="only supports 'Streaming' extras",
    ):

        class _Controller(SSEController[PydanticSerializer]):
            @_custom_modify(extras=_CustomExtras(tag='custom'))
            async def get(self) -> AsyncIterator[SSEvent[int]]:
                return _events()
