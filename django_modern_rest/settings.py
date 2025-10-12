from typing import Any, Final

from django_modern_rest.openapi.config import OpenAPIConfig

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'

#: Names for different settings:
DMR_JSON_SERIALIZER_KEY: Final = 'json_serializer'
DMR_JSON_DESERIALIZER_KEY: Final = 'json_deserializer'
DMR_OPENAPI_CONFIG_KEY: Final = 'openapi_config'

#: Default json serializer.
DMR_JSON_SERIALIZER: Final = 'django_modern_rest.json.serialize'

#: Default json deserializer.
DMR_JSON_DESERIALIZER: Final = 'django_modern_rest.json.deserialize'

#: Default OpenAPI config.
DMR_OPENAPI_CONFIG: Final = OpenAPIConfig(
    title='Modern Rest',
    version='0.1.0',
)

_DEFAULTS: Final = {  # noqa: WPS407
    DMR_JSON_SERIALIZER_KEY: DMR_JSON_SERIALIZER,
    DMR_JSON_DESERIALIZER_KEY: DMR_JSON_DESERIALIZER,
    DMR_OPENAPI_CONFIG_KEY: DMR_OPENAPI_CONFIG,
}


def resolve_defaults() -> dict[str, Any]:
    """Resolve defaults for `django-modern-rest` settings."""
    from django.conf import settings  # noqa: PLC0415

    return getattr(settings, DMR_SETTINGS, _DEFAULTS)
