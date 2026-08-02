from typing import final

from typing_extensions import override

from dmr.security.token import HeaderTokenAsyncAuth, HeaderTokenSyncAuth
from dmr.security.token.token import TokenLikeAsync, TokenLikeSync
from server.apps.token_custom_user.models import ApiToken, ApiUser


@final
class HeaderApiTokenSyncAuth(HeaderTokenSyncAuth):
    @property
    @override  # Note, that both the token and the `User` model are custom:
    def token_model(self) -> type[TokenLikeSync[ApiUser]]:
        return ApiToken


@final
class HeaderApiTokenAsyncAuth(HeaderTokenAsyncAuth):
    @property
    @override
    def token_model(self) -> type[TokenLikeAsync[ApiUser]]:
        return ApiToken
