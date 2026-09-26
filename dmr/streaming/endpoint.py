import dataclasses
from typing import TYPE_CHECKING, Final, Self, final

from typing_extensions import Sentinel, override

from dmr.exceptions import EndpointMetadataError
from dmr.internal.endpoint import Extras, ModifyEndpoint, ValidateEndpoint
from dmr.settings import Settings, resolve_setting
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer
    from dmr.validation import EndpointMetadataBuilder


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class StreamingExtras:
    """
    Resolved streaming settings of an endpoint.

    It is stored in :attr:`~dmr.metadata.EndpointMetadata.extras`
    for all endpoints of streaming controllers.

    Attributes:
        validate_events: Should this endpoint validate events?

    .. versionadded:: 0.16.0
    """

    validate_events: bool


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Streaming(Extras[StreamingExtras]):
    """
    Extra settings for endpoints of streaming controllers.

    Pass it as ``extras=`` to :data:`~dmr.streaming.modify`
    or :data:`~dmr.streaming.validate`.
    It can only be used with streaming controllers.

    Set it as ``extras`` on a controller to provide controller-level
    defaults, for example: ``extras = Streaming(validate_events=False)``.

    Attributes:
        validate_events: Should this endpoint validate events?
            If not set, defaults to the controller value,
            then to :data:`~dmr.settings.Settings.validate_events`,
            then to the ``validate_responses`` value.

    .. versionadded:: 0.16.0
    """

    validate_events: bool | Sentinel = EMPTY

    @classmethod
    @override
    def build(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,  # TODO: this looks like a pyright bug
        from_endpoint: Self | Sentinel,
        from_controller: Self,
        controller_cls: type['Controller[BaseSerializer]'],
        builder: 'EndpointMetadataBuilder',
    ) -> StreamingExtras:
        """Resolve streaming settings from all configuration layers."""
        if not controller_cls.streaming:
            raise EndpointMetadataError(
                f'Cannot apply streaming extras {from_endpoint!r} '
                f'to non-streaming controller: {controller_cls!r}',
            )
        return StreamingExtras(
            validate_events=cls._build_validate_events(
                from_endpoint,
                from_controller,
                builder,
            ),
        )

    @classmethod
    def _build_validate_events(
        cls,
        from_endpoint: Self | Sentinel,
        from_controller: Self,
        builder: 'EndpointMetadataBuilder',
    ) -> bool:
        settings_value: bool | Sentinel = resolve_setting(
            Settings.validate_events,
        )
        validate_events = builder.merger('validate_events').first_set(
            (
                EMPTY
                if isinstance(from_endpoint, Sentinel)
                else from_endpoint.validate_events
            ),
            from_controller.validate_events,
            settings_value,
        )
        if isinstance(validate_events, Sentinel):
            return builder.build_validate_responses()
        return validate_events


#: Same as :data:`dmr.modify`, but supports ``extras=Streaming(...)``.
modify: Final = ModifyEndpoint(Streaming)

#: Same as :data:`dmr.validate`, but supports ``extras=Streaming(...)``.
validate: Final = ValidateEndpoint(Streaming)
