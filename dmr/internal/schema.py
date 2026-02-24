from typing import Any


def get_schema_name(source_type: Any) -> str:
    """
    Returns schema name for a model.

    First tries custom ``__dmr_schema_name__``, then ``__name__``,
    fallbacks to some random name.
    """
    custom_name: str | None = getattr(source_type, '__dmr_schema_name__', None)
    if custom_name is not None:
        return custom_name
    original_name: str | None = getattr(source_type, '__qualname__', None)
    if original_name is not None:
        return original_name
    raise NotImplementedError(
        f'Schema name for {source_type} cannot be generated',
    )
