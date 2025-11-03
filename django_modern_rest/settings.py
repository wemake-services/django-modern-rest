import enum
import os
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Final, final

from django.utils import module_loading

from django_modern_rest.openapi.config import OpenAPIConfig

# Settings with env vars only
# ---------------------------

MAX_CACHE_SIZE: Final = int(os.environ.get('DMR_MAX_CACHE_SIZE', '256'))


# Settings with `settings.py`
# ---------------------------

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'


@final
@enum.unique
class Settings(enum.StrEnum):
    """Keys for all settings."""

    serialize = 'serialize'
    deserialize = 'deserialize'
    validate_responses = 'validate_responses'
    responses = 'responses'
    global_error_handler = 'global_error_handler'
    openapi_config = 'openapi_config'


#: Default settings for `django_modern_rest`.
_DEFAULTS: Final[Mapping[str, Any]] = {  # noqa: WPS407
    Settings.serialize: 'django_modern_rest.internal.json.serialize',
    Settings.deserialize: ('django_modern_rest.internal.json.deserialize'),
    Settings.openapi_config: OpenAPIConfig(
        title='Django Modern Rest',
        version='0.1.0',
    ),
    # Means that we would run extra validation on the response object.
    Settings.validate_responses: True,
    Settings.responses: [],  # global responses, for response validation
    Settings.global_error_handler: (
        'django_modern_rest.errors.global_error_handler'
    ),
}


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _resolve_defaults() -> Mapping[str, Any]:
    """
    Resolve all ``django-modern-rest`` settings with defaults.

    The result is cached using ``@lru_cache`` for performance.
    When testing with custom settings, you *must* call
    :func:`clear_settings_cache` before and after modifying
    Django settings to ensure the cache is invalidated properly.
    """
    from django.conf import settings  # noqa: PLC0415

    return getattr(settings, DMR_SETTINGS, _DEFAULTS)


@lru_cache(maxsize=MAX_CACHE_SIZE)
def resolve_setting(
    setting_name: Settings,
    *,
    import_string: bool = False,
) -> Any:
    """
    Resolves setting by *setting_name*.

    The result is cached using ``@lru_cache`` for performance.
    When testing with custom settings, you *must* call
    :func:`clear_settings_cache` before and after modifying
    Django settings to ensure the cache is invalidated properly.
    """
    setting = _resolve_defaults().get(
        setting_name,
        _DEFAULTS[setting_name],
    )
    if import_string and isinstance(setting, str):
        return module_loading.import_string(setting)
    return setting


def clear_settings_cache() -> None:
    """
    Clears settings cache for all functions in this module.

    Useful for tests, when you modify the global settings object.
    """
    _resolve_defaults.cache_clear()
    resolve_setting.cache_clear()
