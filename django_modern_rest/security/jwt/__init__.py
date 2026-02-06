# Projects that influenced this module:
# 1. https://github.com/litestar-org/litestar
# 2. https://github.com/jazzband/djangorestframework-simplejwt

try:
    import jwt  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pyjwt` is not installed, '
        "consider using `pip install 'django-modern-rest[jwt]'`",
    )
    raise

from django_modern_rest.security.jwt.auth import JWTAsyncAuth as JWTAsyncAuth
from django_modern_rest.security.jwt.auth import JWTSyncAuth as JWTSyncAuth
from django_modern_rest.security.jwt.token import JWTToken as JWTToken
