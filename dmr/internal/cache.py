import importlib


def clear_settings_cache() -> None:
    """
    Clears settings cache for all functions in this module.

    Useful for tests, when you modify the global settings object.
    """
    to_import = {
        'dmr.plugins.pydantic.serializer': [
            '_get_cached_type_adapter',
        ],
        'dmr.plugins.msgspec.json': [
            '_get_serializer',
            '_get_deserializer',
        ],
        'dmr.settings': [
            '_resolve_defaults',
            'resolve_setting',
        ],
    }

    for module, cached in to_import.items():
        try:
            mod_object = importlib.import_module(module)
        except ImportError:  # pragma: no cover
            continue
        for cached_item in cached:
            getattr(mod_object, cached_item).cache_clear()
