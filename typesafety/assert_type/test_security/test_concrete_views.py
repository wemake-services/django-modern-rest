from collections.abc import Callable
from typing import assert_type

from django.http import HttpResponseBase

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import concrete_views as session_views
from dmr.security.jwt import concrete_views as jwt_views
from dmr.security.token import concrete_views as token_views
from dmr.security.token.app.models import Token

# Every required field is typed:
assert_type(
    jwt_views.ObtainTokensSyncController.as_view(serializer=PydanticSerializer),
    Callable[..., HttpResponseBase],
)
assert_type(
    jwt_views.CookieObtainTokensSyncController.as_view(
        serializer=PydanticSerializer,
        jwt_refresh_cookie_path='/api/auth/refresh/',
    ),
    Callable[..., HttpResponseBase],
)
assert_type(
    token_views.ObtainTokenSyncController.as_view(
        serializer=PydanticSerializer,
        token_cls=Token,
    ),
    Callable[..., HttpResponseBase],
)
assert_type(
    session_views.DjangoSessionSyncController.as_view(
        serializer=PydanticSerializer,
    ),
    Callable[..., HttpResponseBase],
)

# Wrong types are rejected:
jwt_views.ObtainTokensSyncController.as_view(serializer=int)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
jwt_views.CookieObtainTokensSyncController.as_view(
    serializer=PydanticSerializer,
    jwt_refresh_cookie_path=1,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
)
token_views.ObtainTokenSyncController.as_view(
    serializer=PydanticSerializer,
    token_cls=str,  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
)
session_views.DjangoSessionSyncController.as_view(serializer='pydantic')  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
