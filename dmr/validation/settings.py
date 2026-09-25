import dataclasses
import types
from collections.abc import Sequence
from typing import Any, ClassVar, Final, TypeAlias

from dmr.exceptions import EndpointMetadataError
from dmr.internal.enums import stringify
from dmr.metadata import ResponseSpec, ResponseSpecProvider
from dmr.openapi import OpenAPIConfig
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.security import AsyncAuth, SyncAuth, SyncOrAsyncAuth
from dmr.semantic_schema import AuthProvider
from dmr.serializer import BaseSerializer
from dmr.settings import (
    Settings,
    SettingsDict,
    _resolve_defaults,  # pyright: ignore[reportPrivateUsage]
)
from dmr.throttling import AsyncThrottle, SyncOrAsyncThrottle, SyncThrottle
from dmr.types import EMPTY


class _SettingsModel(SettingsDict, total=False):
    """
    Settings model that can be validated by our serializers.

    We redefine all unsupported fields with ``Any`` types here.
    """

    parsers: Sequence[Any]
    renderers: Sequence[Any]
    auth: Sequence[Any]
    throttling: Sequence[Any]
    responses: Sequence[Any]
    semantic_schema_providers: Sequence[Any]
    openapi_config: Any
    global_error_handler: Any
    # `EMPTY` sentinel is not supported by serializers:
    semantic_responses: Any
    semantic_auth: Any
    validate_negotiation: Any
    validate_events: Any
    openapi_examples_seed: Any


assert _SettingsModel.__optional_keys__ == set(Settings), (  # noqa: S101
    'Settings enum and its type _SettingsModel have different keys'
)

_AllowedTypes: TypeAlias = tuple[type, ...]

# Sequence settings and the types their items are allowed to have:
_SEQUENCE_TYPES: Final = types.MappingProxyType({
    'parsers': (Parser,),
    'renderers': (Renderer,),
    'auth': (SyncAuth, AsyncAuth, SyncOrAsyncAuth),
    'throttling': (SyncThrottle, AsyncThrottle, SyncOrAsyncThrottle),
    'responses': (ResponseSpec,),
    'semantic_schema_providers': (ResponseSpecProvider, AuthProvider),
})


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class SettingsValidator:
    """Validates defined settings once."""

    serializer: type[BaseSerializer]

    # Flag to only validate settings once:
    is_validated: ClassVar[bool] = False

    def __call__(self) -> None:
        """Collect and validate settings."""
        if self.is_validated:
            return

        settings = self._validate_structure()
        self._validate_types(settings)
        self.__class__.is_validated = True

    def _validate_structure(self) -> _SettingsModel:
        settings = _resolve_defaults()
        try:
            self.serializer.from_python(
                {
                    # msgspec does not like `StrEnum` keys:
                    stringify(setting_key): (
                        # For some reason `pydantic` does not validate
                        # `set[str]` against `collections.abc.Set[str]`
                        frozenset(setting_value)  # pyright: ignore[reportUnknownArgumentType]
                        if isinstance(setting_value, set)
                        else setting_value
                    )
                    for setting_key, setting_value in settings.items()
                },
                model=_SettingsModel,
                strict=True,
            )
        except self.serializer.validation_error as exc:
            raise EndpointMetadataError('Settings validation failed') from exc
        return settings  # type: ignore[return-value]

    def _validate_types(
        self,
        settings: _SettingsModel,
    ) -> None:
        # Some types are not compatible with pydantic / msgspec validation.
        # So, we validate them by hands.
        self._validate_sequence_types(settings)
        self._validate_scalar_types(settings)

    def _validate_sequence_types(
        self,
        settings: _SettingsModel,
    ) -> None:
        for setting_name, allowed_types in _SEQUENCE_TYPES.items():
            sequence: Sequence[Any] = settings.get(setting_name, ())  # type: ignore[assignment]
            if not all(
                isinstance(element, allowed_types) for element in sequence
            ):
                type_names = ', '.join(
                    allowed_type.__name__ for allowed_type in allowed_types
                )
                raise EndpointMetadataError(
                    f'Settings.{setting_name} must all be instances of: '
                    f'{type_names}',
                )

    def _validate_scalar_types(
        self,
        settings: _SettingsModel,
    ) -> None:
        openapi_config = settings.get('openapi_config', EMPTY)
        if openapi_config is not EMPTY and not isinstance(
            openapi_config,
            OpenAPIConfig,
        ):
            raise EndpointMetadataError(
                'Settings.openapi_config must be an OpenAPIConfig instance',
            )

        global_error_handler = settings.get('global_error_handler', EMPTY)
        if global_error_handler is not EMPTY and not (
            isinstance(global_error_handler, str)
            or callable(global_error_handler)
        ):
            raise EndpointMetadataError(
                'Settings.global_error_handler must be a string or callable',
            )

        self._validate_empty_scalars(settings)

    def _validate_empty_scalars(
        self,
        settings: _SettingsModel,
    ) -> None:
        # These values can be `EMPTY`, which serializers do not understand:
        for flag_name in (
            'semantic_responses',
            'semantic_auth',
            'validate_negotiation',
            'validate_events',
        ):
            flag = settings.get(flag_name, EMPTY)
            if flag is not EMPTY and not isinstance(flag, bool):
                raise EndpointMetadataError(
                    f'Settings.{flag_name} must be a bool or EMPTY',
                )

        examples_seed = settings.get('openapi_examples_seed', EMPTY)
        if examples_seed is not EMPTY and not isinstance(examples_seed, int):
            raise EndpointMetadataError(
                'Settings.openapi_examples_seed must be an int or EMPTY',
            )
