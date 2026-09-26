import dataclasses
from typing import TYPE_CHECKING, Self, final

from typing_extensions import Sentinel

from dmr.controller import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, resolve_setting
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.validation import EndpointMetadataBuilder


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class StreamingExtras:
    validate_events: bool


@final
@dataclasses.dataclass(slots=True, frozen=True)
class Streaming:
    validate_events: bool | Sentinel = EMPTY

    @classmethod
    def build(
        cls,
        payload_extras: Self | Sentinel,
        controller_cls: type[Controller[BaseSerializer]],
        builder: 'EndpointMetadataBuilder',
    ) -> StreamingExtras:
        if (
            not isinstance(payload_extras, Sentinel)
            and not controller_cls.streaming
        ):
            raise EndpointMetadataError(
                f'Cannot apply streaming metadata {payload_extras} '
                f'to non-streaming controller: {controller_cls}',
            )
        return StreamingExtras(
            validate_events=cls._build_validate_events(
                payload_extras,
                controller_cls,
                builder,
            ),
        )

    @classmethod
    def _build_validate_events(
        cls,
        payload_extras: Self | Sentinel,
        controller_cls: type[Controller[BaseSerializer]],
        builder: 'EndpointMetadataBuilder',
    ) -> bool:
        merger = builder._merger('validate_events')
        settings_value: bool | Sentinel = resolve_setting(
            Settings.validate_events,
        )
        validate_events = merger.first_set(
            (
                EMPTY
                if isinstance(payload_extras, Sentinel)
                else payload_extras.validate_events
            ),
            controller_cls.validate_events,
            settings_value,
        )
        if isinstance(validate_events, Sentinel):
            return builder._build_validate_responses()
        return validate_events
