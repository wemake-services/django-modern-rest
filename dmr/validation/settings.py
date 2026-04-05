import dataclasses
from collections.abc import Sequence
from typing import Any, ClassVar, cast

from dmr.exceptions import EndpointMetadataError
from dmr.metadata import ResponseSpec
from dmr.openapi import OpenAPIConfig
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.security import AsyncAuth, SyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import (
    Settings,
    SettingsDict,
    _resolve_defaults,  # pyright: ignore[reportPrivateUsage]
)
from dmr.types import EmptyObj


class _SettingsModel(SettingsDict, total=False):
    """
    Settings model that can be validated by our serializers.

    We redefine all unsupported fields with ``Any`` types here.
    """

    parsers: Sequence[Any]  # type: ignore[misc]
    renderers: Sequence[Any]  # type: ignore[misc]
    auth: Sequence[Any]  # type: ignore[misc]
    responses: Sequence[Any]  # type: ignore[misc]
    openapi_config: Any  # type: ignore[misc]
    global_error_handler: Any  # type: ignore[misc]


assert _SettingsModel.__optional_keys__ == set(Settings), (  # noqa: S101
    'Settings enum and its type _SettingsModel have different keys'
)


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
                    str(setting_key): (
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
        return cast(_SettingsModel, settings)

    def _validate_types(  # noqa: C901, WPS231, WPS238
        self,
        settings: _SettingsModel,
    ) -> None:
        # Some types are not compatible with pydantic / msgspec validation.
        # So, we validate them by hands.
        if not all(
            isinstance(parser, Parser) for parser in settings.get('parsers', [])
        ):
            raise EndpointMetadataError(
                'Settings.parsers must all be Parser instances',
            )

        # Renderers:
        if not all(
            isinstance(renderer, Renderer)
            for renderer in settings.get('renderers', [])
        ):
            raise EndpointMetadataError(
                'Settings.renderers must all be Renderer instances',
            )

        # Auth:
        if not all(
            isinstance(auth, (SyncAuth, AsyncAuth))
            for auth in settings.get('auth', [])
        ):
            raise EndpointMetadataError(
                'Settings.auth must all be SyncAuth or AsyncAuth instances',
            )

        # Responses:
        if not all(
            isinstance(response, ResponseSpec)
            for response in settings.get('responses', [])
        ):
            raise EndpointMetadataError(
                'Settings.responses must all be ResponseSpec instances',
            )

        openapi_config = settings.get('openapi_config', EmptyObj)
        if openapi_config is not EmptyObj and not isinstance(
            openapi_config,
            OpenAPIConfig,
        ):
            raise EndpointMetadataError(
                'Settings.openapi_config must be an OpenAPIConfig instance',
            )

        global_error_handler = settings.get('global_error_handler', EmptyObj)
        if global_error_handler is not EmptyObj and not (
            isinstance(global_error_handler, str)
            or callable(global_error_handler)
        ):
            raise EndpointMetadataError(
                'Settings.global_error_handler must be a string or callable',
            )
