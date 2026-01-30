def clear_settings_cache() -> None:  # noqa: C901
    """
    Clears settings cache for all functions in this module.

    Useful for tests, when you modify the global settings object.
    """
    try:
        from django_modern_rest.plugins.pydantic.serializer import (  # noqa: PLC0415
            _get_cached_type_adapter,  # pyright: ignore[reportPrivateUsage]
        )
    except ImportError:  # pragma: no cover
        pass  # noqa: WPS420
    else:
        _get_cached_type_adapter.cache_clear()

    try:
        from django_modern_rest.plugins.msgspec.json import (  # noqa: PLC0415
            _get_serializer,  # pyright: ignore[reportPrivateUsage]
        )
    except ImportError:  # pragma: no cover
        pass  # noqa: WPS420
    else:
        _get_serializer.cache_clear()

    try:
        from django_modern_rest.plugins.msgspec.json import (  # noqa: PLC0415
            _get_deserializer,  # pyright: ignore[reportPrivateUsage]
        )
    except ImportError:  # pragma: no cover
        pass  # noqa: WPS420
    else:
        _get_deserializer.cache_clear()

    from django_modern_rest.validation.response import (  # noqa: PLC0415
        _is_validation_enabled,  # pyright: ignore[reportPrivateUsage]
    )

    _is_validation_enabled.cache_clear()

    from django_modern_rest.settings import (  # noqa: PLC0415
        _resolve_defaults,  # pyright: ignore[reportPrivateUsage]
        resolve_setting,
    )

    _resolve_defaults.cache_clear()
    resolve_setting.cache_clear()
