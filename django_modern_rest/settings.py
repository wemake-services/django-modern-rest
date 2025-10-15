import types
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Final

from django_modern_rest.openapi.config import OpenAPIConfig

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'

#: Names for different settings:
DMR_SERIALIZE_KEY: Final = 'serialize'
DMR_DESERIALIZE_KEY: Final = 'deserialize'
DMR_VALIDATE_RESPONSE_KEY: Final = 'validate_responses'
DMR_OPENAPI_CONFIG_KEY: Final = 'openapi_config'

#: Default json serializer.
DMR_SERIALIZE: Final = 'django_modern_rest.internal.json.serialize'

#: Default json deserializer.
DMR_DESERIALIZE: Final = 'django_modern_rest.internal.json.deserialize'

#: Default OpenAPI config.
DMR_OPENAPI_CONFIG: Final = OpenAPIConfig(
    title='Modern Rest',
    version='0.1.0',
)

#: Default settings for `django_modern_rest`.
_DEFAULTS: Final = types.MappingProxyType({
    DMR_SERIALIZE_KEY: DMR_SERIALIZE,
    DMR_DESERIALIZE_KEY: DMR_DESERIALIZE,
    DMR_OPENAPI_CONFIG_KEY: DMR_OPENAPI_CONFIG,
    # Means that we would run extra validation on the response object.
    DMR_VALIDATE_RESPONSE_KEY: True,
})


# TODO: document that settings need `.cache_clear` in tests.
@lru_cache
def resolve_defaults() -> Mapping[str, Any]:
    """Resolves all settings with defaults."""
    from django.conf import settings  # noqa: PLC0415

    return getattr(settings, DMR_SETTINGS, _DEFAULTS)


@lru_cache
def resolve_setting(setting_name: str, *, model: Any | None = None) -> Any:
    """Resolves setting by *setting_name*."""
    return resolve_defaults().get(setting_name, _DEFAULTS[setting_name])
