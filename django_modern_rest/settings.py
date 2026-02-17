import enum
import importlib
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final, final

from django.utils import module_loading

from django_modern_rest.envs import MAX_CACHE_SIZE
from django_modern_rest.internal.cache import (
    clear_settings_cache as clear_settings_cache,
)
from django_modern_rest.openapi.config import OpenAPIConfig

if TYPE_CHECKING:
    from django_modern_rest.parsers import Parser
    from django_modern_rest.renderers import Renderer

try:
    import msgspec  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    # We do that so `lint-imports` won't trigger :)
    default_parser: 'Parser' = importlib.import_module(
        'django_modern_rest.parsers',
    ).JsonParser()
    default_renderer: 'Renderer' = importlib.import_module(
        'django_modern_rest.renderers',
    ).JsonRenderer()
else:  # pragma: no cover
    # We do that so `lint-imports` won't trigger :)
    plugin = importlib.import_module('django_modern_rest.plugins.msgspec')
    MsgspecJsonParser = plugin.MsgspecJsonParser
    MsgspecJsonRenderer = plugin.MsgspecJsonRenderer
    del plugin  # noqa: WPS420

    default_parser = MsgspecJsonParser()
    default_renderer = MsgspecJsonRenderer()


# Settings with `settings.py`
# ---------------------------

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'


@final
@enum.unique
class Settings(enum.StrEnum):
    """Keys for all settings."""

    parsers = 'parsers'
    renderers = 'renderers'
    auth = 'auth'
    no_validate_http_spec = 'no_validate_http_spec'
    validate_responses = 'validate_responses'
    responses = 'responses'
    global_error_handler = 'global_error_handler'
    openapi_config = 'openapi_config'
    django_treat_as_post = 'django_treat_as_post'


@final
@enum.unique
class HttpSpec(enum.StrEnum):
    """
    Keys for our HTTP spec validation.

    All rules can be disabled per endpoint, per blueprint, and per controller.
    You can disable any of the validation rules we have here globally by:

    .. code:: python

      >>> DMR_SETTINGS = {
      ...     Settings.no_validate_http_spec: {
      ...         HttpSpec.empty_response_body,
      ...     },
      ... }

    Attributes:
        empty_request_body: Disables validation that methods
            like ``GET`` and ``HEAD`` can't have request bodies.
        empty_response_body: Disables validation that some status codes
            like ``204`` must not have response bodies.

    """

    empty_request_body = 'empty_request_body'
    empty_response_body = 'empty_response_body'


#: Default settings for `django_modern_rest`.
_DEFAULTS: Final[Mapping[str, Any]] = {  # noqa: WPS407
    Settings.parsers: [default_parser],
    Settings.renderers: [default_renderer],
    Settings.auth: [],
    Settings.openapi_config: OpenAPIConfig(
        title='Django Modern Rest',
        version='0.1.0',
    ),
    # We validate some HTTP spec things by default to be strict,
    # can be disabled:
    Settings.no_validate_http_spec: frozenset(),
    # Means that we would run extra validation on the response object.
    Settings.validate_responses: True,
    Settings.responses: [],  # global responses, for response validation
    Settings.global_error_handler: (
        'django_modern_rest.errors.global_error_handler'
    ),
    # Settings for middleware:
    Settings.django_treat_as_post: frozenset(('PUT', 'PATCH')),
}

assert all(setting_key in _DEFAULTS for setting_key in Settings), (  # noqa: S101
    'Some Settings keys do not have default values'
)


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
    return setting  # pyright: ignore[reportUnknownVariableType]
