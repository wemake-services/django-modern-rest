import enum
import importlib
from collections.abc import Callable, Mapping, Sequence, Set
from functools import lru_cache
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, final

from django.utils import module_loading
from typing_extensions import TypedDict

from dmr.envs import MAX_CACHE_SIZE
from dmr.internal.cache import clear_settings_cache as clear_settings_cache
from dmr.openapi.config import OpenAPIConfig

if TYPE_CHECKING:
    from dmr.metadata import ResponseSpec
    from dmr.openapi import OpenAPIConfig
    from dmr.parsers import Parser
    from dmr.renderers import Renderer
    from dmr.security import AsyncAuth, SyncAuth

try:
    import msgspec  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    # We do that so `lint-imports` won't trigger :)
    default_parser: 'Parser' = importlib.import_module(
        'dmr.parsers',
    ).JsonParser()
    default_renderer: 'Renderer' = importlib.import_module(
        'dmr.renderers',
    ).JsonRenderer()
else:  # pragma: no cover
    # We do that so `lint-imports` won't trigger :)
    plugin = importlib.import_module('dmr.plugins.msgspec')
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
    semantic_responses = 'semantic_responses'
    exclude_semantic_responses = 'exclude_semantic_responses'
    validate_events = 'validate_events'
    responses = 'responses'
    global_error_handler = 'global_error_handler'
    openapi_config = 'openapi_config'
    openapi_examples_seed = 'openapi_examples_seed'
    django_treat_as_post = 'django_treat_as_post'
    openapi_static_cdn = 'openapi_static_cdn'


@final
@enum.unique
class HttpSpec(enum.StrEnum):
    """
    Keys for our HTTP spec validation.

    All rules can be disabled per endpoint and per controller.
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


class SettingsDict(TypedDict, total=False):
    """Settings type that can be used for typing."""

    parsers: Sequence['Parser']
    renderers: Sequence['Renderer']
    auth: Sequence['AsyncAuth | SyncAuth']
    no_validate_http_spec: Set[HttpSpec]
    validate_responses: bool
    semantic_responses: bool
    exclude_semantic_responses: Set[HTTPStatus]
    validate_events: bool | None
    responses: Sequence['ResponseSpec']
    global_error_handler: Callable[[Any, Any, Any], Any] | str
    openapi_config: 'OpenAPIConfig'
    openapi_examples_seed: int | None
    django_treat_as_post: Set[str]
    openapi_static_cdn: dict[str, str]


assert SettingsDict.__optional_keys__ == set(Settings), (  # noqa: S101
    'Settings enum and its type SettingsDict have different keys'
)


#: Default settings for `django-modern-rest`.
_DEFAULTS: Final[Mapping[str, Any]] = {  # noqa: WPS407
    Settings.parsers: [default_parser],
    Settings.renderers: [default_renderer],
    Settings.auth: [],
    # OpenAPI settings:
    Settings.openapi_config: OpenAPIConfig(
        title='Django Modern Rest',
        version='0.1.0',
    ),
    Settings.openapi_examples_seed: None,  # turned off by default
    # We validate some HTTP spec things by default to be strict,
    # can be disabled:
    Settings.no_validate_http_spec: frozenset(),
    # Means that we would run extra validation on the response object.
    Settings.validate_responses: True,
    Settings.semantic_responses: True,
    Settings.exclude_semantic_responses: frozenset(),
    # Defaults to the `validate_responses` setting if `None`:
    Settings.validate_events: None,
    Settings.responses: [],  # global responses, for response validation
    Settings.global_error_handler: 'dmr.errors.global_error_handler',
    # Settings for middleware:
    Settings.django_treat_as_post: frozenset(('PUT', 'PATCH')),
    # OpenAPI static CDN configuration:
    Settings.openapi_static_cdn: {},
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
