import types
from collections.abc import Mapping
from typing import Any, Final

from django_modern_rest.openapi.config import OpenAPIConfig

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'

#: Names for different settings:
DMR_JSON_SERIALIZE_KEY: Final = 'json_serialize'
DMR_JSON_DESERIALIZE_KEY: Final = 'json_deserialize'
DMR_OPENAPI_CONFIG_KEY: Final = 'openapi_config'

#: Default json serializer.
DMR_JSON_SERIALIZE: Final = 'django_modern_rest.internal.json.serialize'

#: Default json deserializer.
DMR_JSON_DESERIALIZE: Final = 'django_modern_rest.internal.json.deserialize'

#: Default OpenAPI config.
DMR_OPENAPI_CONFIG: Final = OpenAPIConfig(
    title='Modern Rest',
    version='0.1.0',
)

_DEFAULTS: Final = types.MappingProxyType({
    DMR_JSON_SERIALIZE_KEY: DMR_JSON_SERIALIZE,
    DMR_JSON_DESERIALIZE_KEY: DMR_JSON_DESERIALIZE,
    DMR_OPENAPI_CONFIG_KEY: DMR_OPENAPI_CONFIG,
})


def resolve_defaults() -> Mapping[str, Any]:
    from django.conf import settings  # noqa: PLC0415

    return getattr(settings, DMR_SETTINGS, _DEFAULTS)
