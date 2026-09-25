from typing import Any, Final, TypeAlias, final

import pytest
from django.conf import LazySettings

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.security.base import SyncOrAsyncAuth
from dmr.security.django_session import concrete_views as session_views
from dmr.security.jwt import HeaderJWTAsyncAuth, HeaderJWTSyncAuth
from dmr.security.jwt import concrete_views as jwt_views
from dmr.security.token import concrete_views as token_views
from dmr.security.token.app.models import Token
from dmr.security.token.token import TokenLikeSync
from dmr.serializer import BaseSerializer
from dmr.settings import Settings

_AnyController: TypeAlias = type[Controller[Any]]

_Serializers: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializers] = [
    PydanticSerializer,
    PydanticFastSerializer,
]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)

#: Every concrete view we ship, each has its own `as_view` override.
_CONCRETE_VIEWS: Final[tuple[_AnyController, ...]] = (
    jwt_views.ObtainTokensSyncController,
    jwt_views.ObtainTokensAsyncController,
    jwt_views.RefreshTokenSyncController,
    jwt_views.RefreshTokenAsyncController,
    jwt_views.VerifyTokenSyncController,
    jwt_views.VerifyTokenAsyncController,
    jwt_views.CookieObtainTokensSyncController,
    jwt_views.CookieObtainTokensAsyncController,
    jwt_views.CookieRefreshTokensSyncController,
    jwt_views.CookieRefreshTokensAsyncController,
    jwt_views.CookieLogoutSyncController,
    jwt_views.CookieLogoutAsyncController,
    token_views.ObtainTokenSyncController,
    token_views.ObtainTokenAsyncController,
    session_views.DjangoSessionSyncController,
    session_views.DjangoSessionAsyncController,
)

_COOKIE_VIEWS: Final = (
    jwt_views.CookieObtainTokensSyncController,
    jwt_views.CookieObtainTokensAsyncController,
    jwt_views.CookieRefreshTokensSyncController,
    jwt_views.CookieRefreshTokensAsyncController,
    jwt_views.CookieLogoutSyncController,
    jwt_views.CookieLogoutAsyncController,
)

_TOKEN_VIEWS: Final = (
    token_views.ObtainTokenSyncController,
    token_views.ObtainTokenAsyncController,
)


def _get_custom_token_model() -> type[TokenLikeSync]:
    from server.apps.token_auth.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        CustomToken,
    )

    return CustomToken  # type: ignore[no-any-return]


def _assert_routable(routed_cls: _AnyController) -> None:
    assert not routed_cls.is_abstract
    assert routed_cls.api_endpoints


@pytest.mark.parametrize('view_cls', _CONCRETE_VIEWS)
def test_as_view_with_serializer(view_cls: _AnyController) -> None:
    """Ensures that a serializer is all a concrete view needs."""
    view = view_cls.as_view(serializer=PydanticSerializer)

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.serializer is PydanticSerializer
    assert issubclass(routed_cls, view_cls)
    assert routed_cls.__name__ == view_cls.__name__
    assert routed_cls.__qualname__ == view_cls.__qualname__
    assert routed_cls.__module__ == view_cls.__module__
    # Our docstrings describe the library, they must not end up
    # as `summary` and `description` in the API schema of users:
    assert routed_cls.__doc__ is None


@pytest.mark.parametrize('view_cls', _CONCRETE_VIEWS)
@pytest.mark.parametrize('serializer', serializers)
def test_as_view_leaves_the_view_alone(
    view_cls: _AnyController,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that routing a concrete view does not mutate it."""
    view = view_cls.as_view(serializer=serializer)

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.serializer is serializer
    assert view_cls.is_abstract
    assert getattr(view_cls, 'serializer', None) is None


@pytest.mark.parametrize('view_cls', _CONCRETE_VIEWS)
def test_as_view_without_serializer(view_cls: _AnyController) -> None:
    """Ensures that a concrete view still needs its serializer."""
    with pytest.raises(EndpointMetadataError, match='is abstract'):
        view_cls.as_view()


@pytest.mark.parametrize('view_cls', _COOKIE_VIEWS)
def test_as_view_with_refresh_cookie_path(
    view_cls: type[jwt_views.CookieObtainTokensSyncController[Any]],
) -> None:
    """Ensures that the refresh cookie path can be given to `as_view`."""
    view = view_cls.as_view(
        serializer=PydanticSerializer,
        jwt_refresh_cookie_path='/api/auth/refresh/',
    )

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.jwt_refresh_cookie_path == '/api/auth/refresh/'
    assert routed_cls.refresh_cookie_spec().path == '/api/auth/refresh/'
    assert view_cls.jwt_refresh_cookie_path == '/'


@pytest.mark.parametrize('view_cls', _TOKEN_VIEWS)
def test_as_view_with_token_cls(
    view_cls: type[token_views.ObtainTokenSyncController[Any]],
) -> None:
    """Ensures that `token_cls` given to `as_view` beats the default."""
    view = view_cls.as_view(
        serializer=PydanticSerializer,
        token_cls=_get_custom_token_model(),
    )

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.token_cls is _get_custom_token_model()


@pytest.mark.parametrize('view_cls', _TOKEN_VIEWS)
def test_as_view_default_token_cls(
    view_cls: type[token_views.ObtainTokenSyncController[Any]],
) -> None:
    """Ensures that the bundled model is used when none is given."""
    view = view_cls.as_view(serializer=PydanticSerializer)

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.token_cls is Token


@final
class _ConcreteSubclass(
    jwt_views.CookieObtainTokensSyncController[PydanticSerializer],
):
    """Already has its serializer, the usual way."""


def test_subclass_as_view() -> None:
    """Ensures that subclasses are routed the usual way."""
    view = _ConcreteSubclass.as_view()

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls is _ConcreteSubclass


def test_subclass_as_view_fills_other_fields() -> None:
    """Ensures that a subclass can still be given the rest of its fields."""
    view = _ConcreteSubclass.as_view(jwt_refresh_cookie_path='/refresh/')

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.serializer is PydanticSerializer
    assert routed_cls.jwt_refresh_cookie_path == '/refresh/'
    assert issubclass(routed_cls, _ConcreteSubclass)


def test_subclass_as_view_serializer() -> None:
    """Ensures that a serializer cannot be replaced after the fact."""
    with pytest.raises(EndpointMetadataError, match='already has'):
        _ConcreteSubclass.as_view(serializer=PydanticFastSerializer)


def test_as_view_passes_initkwargs() -> None:
    """Ensures that django's `initkwargs` are passed through untouched."""
    view = jwt_views.ObtainTokensSyncController.as_view(
        serializer=PydanticSerializer,
        http_method_names=['post'],
    )

    _assert_routable(view.view_class)  # type: ignore[attr-defined]
    assert view.view_initkwargs == {'http_method_names': ['post']}  # type: ignore[attr-defined]


def test_as_view_rejects_unknown_initkwargs() -> None:
    """Ensures that django still rejects names the controller lacks."""
    with pytest.raises(TypeError, match='invalid keyword'):
        jwt_views.ObtainTokensSyncController.as_view(
            serializer=PydanticSerializer,
            token_cls=Token,
        )


@pytest.fixture
def _settings_auth(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {
        Settings.auth: [
            SyncOrAsyncAuth(HeaderJWTSyncAuth(), HeaderJWTAsyncAuth()),
        ],
    }


@pytest.mark.usefixtures('_settings_auth')
def test_settings_auth_is_applied() -> None:
    """Ensures that the settings auth is really there to be ignored."""

    class _SyncController(Controller[PydanticSerializer]):
        def post(self) -> None:
            raise NotImplementedError

    class _AsyncController(Controller[PydanticSerializer]):
        async def post(self) -> None:
            raise NotImplementedError

    sync_auth = _SyncController.api_endpoints['POST'].metadata.auth
    async_auth = _AsyncController.api_endpoints['POST'].metadata.auth
    assert sync_auth
    assert isinstance(sync_auth[0], HeaderJWTSyncAuth)
    assert async_auth
    assert isinstance(async_auth[0], HeaderJWTAsyncAuth)


@pytest.mark.usefixtures('_settings_auth')
@pytest.mark.parametrize('view_cls', _CONCRETE_VIEWS)
def test_concrete_views_ignore_settings_auth(view_cls: _AnyController) -> None:
    """Ensures that auth from the settings is never required to log in."""
    view = view_cls.as_view(serializer=PydanticSerializer)

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert all(
        endpoint.metadata.auth is None
        for endpoint in routed_cls.api_endpoints.values()
    )


@pytest.mark.usefixtures('_settings_auth')
def test_concrete_subclass_ignores_settings_auth() -> None:
    """Ensures that subclasses written the usual way keep `auth=None`."""

    @final
    class _Subclass(
        token_views.ObtainTokenSyncController[PydanticSerializer],
    ):
        """Has its serializer as a type argument."""

    _assert_routable(_Subclass)
    assert _Subclass.api_endpoints['POST'].metadata.auth is None
