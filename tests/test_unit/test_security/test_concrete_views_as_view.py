from typing import Any, Final, TypeAlias, final

import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.security.django_session import concrete_views as session_views
from dmr.security.jwt import concrete_views as jwt_views
from dmr.security.token import concrete_views as token_views
from dmr.security.token.app.models import Token
from dmr.security.token.token import TokenLikeSync

_AnyController: TypeAlias = type[Controller[Any]]

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


@final
class _ConcreteSubclass(
    jwt_views.CookieObtainTokensSyncController[PydanticSerializer],
):
    """Already has its serializer, the usual way."""


@pytest.mark.parametrize('view_cls', _CONCRETE_VIEWS)
def test_as_view_with_serializer(view_cls: _AnyController) -> None:
    """Ensures that a serializer is all a concrete view needs."""
    view = view_cls.as_view(serializer=PydanticSerializer)

    routed_cls = view.view_class  # type: ignore[attr-defined]
    assert routed_cls.serializer is PydanticSerializer
    assert not routed_cls.is_abstract
    assert issubclass(routed_cls, view_cls)
    assert routed_cls.__name__ == view_cls.__name__
    assert routed_cls.__qualname__ == view_cls.__qualname__
    assert routed_cls.__module__ == view_cls.__module__
    assert routed_cls.__doc__ == view_cls.__doc__


@pytest.mark.parametrize('view_cls', _CONCRETE_VIEWS)
def test_as_view_leaves_the_view_alone(
    view_cls: _AnyController,
) -> None:
    """Ensures that routing a concrete view does not mutate it."""
    view_cls.as_view(serializer=PydanticSerializer)

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

    assert view.view_class.token_cls is _get_custom_token_model()  # type: ignore[attr-defined]


@pytest.mark.parametrize('view_cls', _TOKEN_VIEWS)
def test_as_view_default_token_cls(
    view_cls: type[token_views.ObtainTokenSyncController[Any]],
) -> None:
    """Ensures that the bundled model is used when none is given."""
    view = view_cls.as_view(serializer=PydanticSerializer)

    assert view.view_class.token_cls is Token  # type: ignore[attr-defined]


def test_subclass_as_view() -> None:
    """Ensures that subclasses are routed the usual way."""
    view = _ConcreteSubclass.as_view()

    assert view.view_class is _ConcreteSubclass  # type: ignore[attr-defined]


def test_subclass_as_view_fills_other_fields() -> None:
    """Ensures that a subclass can still be given the rest of its fields."""
    view = _ConcreteSubclass.as_view(jwt_refresh_cookie_path='/refresh/')

    routed_cls = view.view_class  # type: ignore[attr-defined]
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

    assert view.view_initkwargs == {'http_method_names': ['post']}  # type: ignore[attr-defined]


def test_as_view_rejects_unknown_initkwargs() -> None:
    """Ensures that django still rejects names the controller lacks."""
    with pytest.raises(TypeError, match='invalid keyword'):
        jwt_views.ObtainTokensSyncController.as_view(
            serializer=PydanticSerializer,
            token_cls=Token,
        )
