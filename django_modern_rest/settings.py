from collections.abc import Mapping
from functools import cache, lru_cache
from typing import Any, Final, cast

from django.utils import module_loading

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.types import DMRSettings

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'

#: Names for different settings:
DMR_SERIALIZE_KEY: Final = 'serialize'
DMR_DESERIALIZE_KEY: Final = 'deserialize'
DMR_VALIDATE_RESPONSES_KEY: Final = 'validate_responses'
DMR_RESPONSES_KEY: Final = 'responses'
DMR_GLOBAL_ERROR_HANDLER_KEY: Final = 'global_error_handler'
DMR_OPENAPI_CONFIG_KEY: Final = 'openapi_config'

#: Default json serializer.
DMR_SERIALIZE: Final = 'django_modern_rest.internal.json.serialize'

#: Default json deserializer.
DMR_DESERIALIZE: Final = 'django_modern_rest.internal.json.deserialize'

#: Default error handler.
DMR_GLOBAL_ERROR_HANDLER: Final = (
    'django_modern_rest.errors.global_error_handler'
)

#: Default OpenAPI config.
DMR_OPENAPI_CONFIG: Final = OpenAPIConfig(
    title='Modern Rest',
    version='0.1.0',
)


# Typed defaults section


#: Default settings for `django_modern_rest`.
_DEFAULTS: Final[DMRSettings] = cast(
    DMRSettings,
               {
        DMR_SERIALIZE_KEY: DMR_SERIALIZE,
        DMR_DESERIALIZE_KEY: DMR_DESERIALIZE,
        DMR_OPENAPI_CONFIG_KEY: DMR_OPENAPI_CONFIG,
        # Means that we would run extra validation on the response object.
        DMR_VALIDATE_RESPONSES_KEY: True,
        DMR_RESPONSES_KEY: [],  # global responses, for response validation
        DMR_GLOBAL_ERROR_HANDLER_KEY: DMR_GLOBAL_ERROR_HANDLER,
    },
)


@lru_cache
def resolve_defaults() -> Mapping[str, Any]:
    """
    Resolve all ``django-modern-rest`` settings with defaults.

    The result is cached using ``@lru_cache`` for performance.
    When testing with custom settings, you *must* call
    :func:`clear_settings_cache` before and after modifying
    Django settings to ensure the cache is invalidated properly.
    """
    from django.conf import settings  # noqa: PLC0415

    return getattr(settings, DMR_SETTINGS, _DEFAULTS)


@cache
def resolve_setting(setting_name: str, *, import_string: bool = False) -> Any:
    """
    Resolves setting by *setting_name*.

    The result is cached using ``@lru_cache`` for performance.
    When testing with custom settings, you *must* call
    :func:`clear_settings_cache` before and after modifying
    Django settings to ensure the cache is invalidated properly.
    """
    setting = resolve_defaults().get(setting_name, _DEFAULTS[setting_name])
    if import_string and isinstance(setting, str):
        return module_loading.import_string(setting)
    return setting


def clear_settings_cache() -> None:
    """
    Clears settings cache for all functions in this module.

    Useful for tests, when you modify the global settings object.
    """
    resolve_defaults.cache_clear()
    resolve_setting.cache_clear()
