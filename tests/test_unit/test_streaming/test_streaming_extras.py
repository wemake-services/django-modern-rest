import dataclasses
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Final, Self, final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from typing_extensions import Sentinel, override

from dmr import Controller
from dmr.endpoint import Extras, ModifyEndpoint
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.streaming import Streaming, modify
from dmr.streaming.endpoint import StreamingExtras
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRRequestFactory
from dmr.types import EMPTY
from dmr.validation import EndpointMetadataBuilder

#: Default `SSEController` ping interval and a custom one for endpoints:
_SSE_PING: Final = 15.0
_ENDPOINT_PING: Final = 0.5


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _CustomExtras(Extras[str]):
    tag: str | Sentinel = EMPTY

    @classmethod
    @override
    def build(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        from_endpoint: Self | Sentinel,
        from_controller: Self,
        controller_cls: type[Controller[BaseSerializer]],
        builder: EndpointMetadataBuilder,
    ) -> str:
        merger = builder.merger('tag')
        return merger.not_empty(
            merger.first_set(
                EMPTY
                if isinstance(from_endpoint, Sentinel)
                else from_endpoint.tag,
                from_controller.tag,
                'default',
            ),
        )


_custom_modify: Final = ModifyEndpoint(_CustomExtras)


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _RequiredExtras(Extras[str]):
    prefix: str  # required, no default
    tag: str | Sentinel = EMPTY

    @classmethod
    @override
    def build(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        from_endpoint: Self | Sentinel,
        from_controller: Self,
        controller_cls: type[Controller[BaseSerializer]],
        builder: EndpointMetadataBuilder,
    ) -> str:
        merger = builder.merger('tag')
        layer = (
            from_controller
            if isinstance(from_endpoint, Sentinel)
            else from_endpoint
        )
        tag = merger.not_empty(
            merger.first_set(layer.tag, from_controller.tag, 'default'),
        )
        return f'{layer.prefix}:{tag}'


_required_modify: Final = ModifyEndpoint(_RequiredExtras)


def test_extras_fallback_from_settings(settings: LazySettings) -> None:
    """Ensures that `EMPTY` `validate_events` falls back to responses."""
    settings.DMR_SETTINGS = {
        Settings.validate_responses: True,
        Settings.validate_events: EMPTY,
    }

    class _Controller(SSEController[PydanticSerializer]):
        async def get(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.extras == StreamingExtras(
        validate_events=True,
        ping_seconds=_SSE_PING,
    )


def test_extras_configuration_levels() -> None:
    """Ensures that controller defaults are used when extras are not set."""

    class _Controller(SSEController[PydanticSerializer]):
        validate_responses = True
        extras = Streaming(validate_events=False)

        async def get(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

        @modify()
        async def post(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

        @modify(extras=Streaming(validate_events=True))
        async def put(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.extras == StreamingExtras(
        validate_events=False,
        ping_seconds=None,
    )
    assert endpoints['POST'].metadata.extras == StreamingExtras(
        validate_events=False,
        ping_seconds=None,
    )
    assert endpoints['PUT'].metadata.extras == StreamingExtras(
        validate_events=True,
        ping_seconds=None,
    )


def test_ping_seconds_levels() -> None:
    """Ensures that `ping_seconds` is resolved from all levels."""

    class _Custom(SSEController[PydanticSerializer]):
        # Replaces `SSEController.extras` entirely, no merging:
        extras = Streaming(validate_events=False)

        async def get(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

        @modify(extras=Streaming(ping_seconds=_ENDPOINT_PING))
        async def post(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

        @modify(extras=Streaming(ping_seconds=None))
        async def put(self) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

    endpoints = _Custom.api_endpoints
    assert endpoints['GET'].metadata.extras == StreamingExtras(
        validate_events=False,
        ping_seconds=None,
    )
    assert endpoints['POST'].metadata.extras.ping_seconds == pytest.approx(
        _ENDPOINT_PING,
    )
    assert endpoints['PUT'].metadata.extras.ping_seconds is None


def test_extras_on_unsupported_controller() -> None:
    """Ensures that extras raise when the controller does not support them."""
    with pytest.raises(EndpointMetadataError, match='does not support extras'):

        class _Controller(Controller[PydanticSerializer]):
            @modify(extras=Streaming(validate_events=True))
            def get(self) -> int:
                raise NotImplementedError


def test_typed_decorator_unsupported() -> None:
    """Ensures that typed decorators raise without controller extras."""
    with pytest.raises(EndpointMetadataError, match='does not support extras'):

        class _Controller(Controller[PydanticSerializer]):
            @modify()
            def get(self) -> int:
                raise NotImplementedError


def test_typed_decorator_mismatch() -> None:
    """Ensures that typed decorators must match the controller extras."""
    with pytest.raises(EndpointMetadataError, match="uses 'Streaming'"):

        class _Controller(SSEController[PydanticSerializer]):
            @_custom_modify()
            async def get(self) -> AsyncIterator[SSEvent[int]]:
                raise NotImplementedError


def test_wrong_extras_type() -> None:
    """Ensures that extras of a wrong type raise."""
    untyped_modify = ModifyEndpoint[_CustomExtras]()
    with pytest.raises(
        EndpointMetadataError,
        match="only supports 'Streaming' extras",
    ):

        class _Controller(SSEController[PydanticSerializer]):
            @untyped_modify(extras=_CustomExtras(tag='custom'))
            async def get(self) -> AsyncIterator[SSEvent[int]]:
                raise NotImplementedError


def test_streaming_extras_non_streaming() -> None:
    """Ensures that `Streaming` extras require a streaming controller."""
    with pytest.raises(EndpointMetadataError, match='non-streaming controller'):

        class _Controller(Controller[PydanticSerializer]):
            extras = Streaming()

            def get(self) -> int:
                raise NotImplementedError


def test_custom_extras(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that custom controllers can define their own extras."""

    class _Controller(Controller[PydanticSerializer]):
        extras = _CustomExtras(tag='from controller')

        def get(self) -> str:
            return _CustomExtras.of(self)

        @_custom_modify(extras=_CustomExtras(tag='from endpoint'))
        def post(self) -> str:
            return _CustomExtras.of(self)

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.extras == 'from controller'
    assert endpoints['POST'].metadata.extras == 'from endpoint'

    response = _Controller.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.content == b'"from controller"'

    response = _Controller.as_view()(dmr_rf.post('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.content == b'"from endpoint"'


def test_required_extras_fields() -> None:
    """Ensures that extras can have required fields."""

    class _Controller(Controller[PydanticSerializer]):
        extras = _RequiredExtras(prefix='controller')

        def get(self) -> str:
            raise NotImplementedError

        @_required_modify()
        def post(self) -> str:
            raise NotImplementedError

        @_required_modify(extras=_RequiredExtras(prefix='endpoint', tag='set'))
        def put(self) -> str:
            raise NotImplementedError

    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.extras == 'controller:default'
    assert endpoints['POST'].metadata.extras == 'controller:default'
    assert endpoints['PUT'].metadata.extras == 'endpoint:set'


def test_custom_extras_defaults() -> None:
    """Ensures that registering extras without values uses defaults."""

    class _Controller(Controller[PydanticSerializer]):
        extras = _CustomExtras()

        def get(self) -> str:
            raise NotImplementedError

    assert _Controller.api_endpoints['GET'].metadata.extras == 'default'


def test_extras_of_wrong_controller(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that `Extras.of` checks the controller extras type."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            return _CustomExtras.of(self)

    with pytest.raises(
        EndpointMetadataError,
        match="does not use '_CustomExtras'",
    ):
        _Controller.as_view()(dmr_rf.get('/whatever/'))
