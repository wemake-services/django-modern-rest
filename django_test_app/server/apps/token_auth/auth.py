from typing import final

from django.contrib.auth.models import User
from typing_extensions import override

from dmr.security.token import HeaderTokenSyncAuth
from dmr.security.token.token import TokenLikeSync
from server.apps.token_auth.models import CustomToken


@final
class HeaderCustomTokenSyncAuth(HeaderTokenSyncAuth):
    @property
    @override  # Note, that we can also specify custom `User` model:
    def token_model(self) -> type[TokenLikeSync[User]]:
        return CustomToken
