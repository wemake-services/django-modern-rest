from typing import final

from django.contrib.auth.models import User
from typing_extensions import override

from dmr.security.token import HeaderTokenSyncAuth, TokenLikeSync
from server.apps.token_auth.models import CustomToken


@final
class HeaderCustomTokenSyncAuth(HeaderTokenSyncAuth):
    @property
    @override
    def token_model(self) -> type[TokenLikeSync[User]]:
        return CustomToken
