try:
    import pydantic  # noqa: F401
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise


from django_modern_rest.plugins.pydantic.serialization import (
    PydanticSerializer as PydanticSerializer,
)
