try:
    import allauth  # noqa: F401  # type: ignore[import-untyped]  # pyright: ignore[reportUnusedImport, reportMissingTypeStubs]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `django-allauth` is not installed, '
        'consider using `pip install django-allauth`',
    )
    raise

from dmr.security.allauth.auth import (
    XSessionTokenAsyncAuth as XSessionTokenAsyncAuth,
)
from dmr.security.allauth.auth import (
    XSessionTokenSyncAuth as XSessionTokenSyncAuth,
)
from dmr.security.allauth.auth import (
    request_allauth_session as request_allauth_session,
)
