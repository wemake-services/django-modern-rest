try:
    import msgspec  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `msgspec` is not installed, '
        "consider using `pip install 'django-modern-rest[msgspec]'`",
    )
    raise

from django_modern_rest.plugins.msgspec.json import (
    MsgspecJsonParser as MsgspecJsonParser,
)
from django_modern_rest.plugins.msgspec.json import (
    MsgspecJsonRenderer as MsgspecJsonRenderer,
)
from django_modern_rest.plugins.msgspec.serializer import (
    MsgspecSerializer as MsgspecSerializer,
)
