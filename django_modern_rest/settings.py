from typing import Final

#: Base name for `django-modern-rest` settings.
DMR_SETTINGS: Final = 'DMR_SETTINGS'

#: Names for different settings:
DMR_JSON_SERIALIZER_KEY: Final = 'json_serializer'
DMR_JSON_DESERIALIZER_KEY: Final = 'json_deserializer'

#: Default json serializer.
DMR_JSON_SERIALIZER: Final = 'django_modern_rest.json.serializer'

#: Default json deserializer.
DMR_JSON_DESERIALIZER: Final = 'django_modern_rest.json.deserialize'

_DEFAULTS: Final = {
    DMR_JSON_SERIALIZER_KEY: DMR_JSON_SERIALIZER,
    DMR_JSON_DESERIALIZER_KEY: DMR_JSON_DESERIALIZER,
}


def resolve_defaults() -> dict[str, Any]:
    from django.conf import settings

    return getattr(settings, DMR_SETTINGS, _DEFAULTS)
