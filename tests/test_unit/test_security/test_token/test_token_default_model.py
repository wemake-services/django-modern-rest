from typing import final

from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import concrete_views
from dmr.security.token.app.models import Token
from dmr.security.token.token import TokenLikeSync


def _get_custom_token_model() -> type[TokenLikeSync]:
    from server.apps.token_auth.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        CustomToken,
    )

    return CustomToken  # type: ignore[no-any-return]


@final
class _DefaultTokenController(
    concrete_views.ObtainTokenSyncController[PydanticFastSerializer],
):
    """Says nothing about the token model."""


@final
class _DefaultTokenAsyncController(
    concrete_views.ObtainTokenAsyncController[PydanticFastSerializer],
):
    """Says nothing about the token model."""


class _CustomTokenController(
    concrete_views.ObtainTokenSyncController[PydanticFastSerializer],
):
    """Brings its own token model."""

    token_cls = _get_custom_token_model()


def test_token_cls_defaults_to_bundled_model() -> None:
    """Ensures that the bundled `Token` model is the default."""
    assert _DefaultTokenController().token_cls is Token
    assert _DefaultTokenAsyncController().token_cls is Token


def test_token_cls_is_not_overridden() -> None:
    """Ensures that a token model of a subclass is left alone."""
    assert _CustomTokenController().token_cls is _get_custom_token_model()
    assert _CustomTokenController().token_cls is not Token


def test_token_cls_is_inherited() -> None:
    """Ensures that the default is not re-resolved for deeper subclasses."""

    @final
    class _Inherited(_CustomTokenController):
        """Inherits the token model of its base."""

    assert _Inherited().token_cls is _get_custom_token_model()
