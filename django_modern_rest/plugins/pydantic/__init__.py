from typing import final

try:
    import pydantic
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise


@final
class PydanticSerialization:
    """Serializes request and response data as pydantic models."""

    serialize = pydantic
