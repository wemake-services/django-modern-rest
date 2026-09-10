from typing_extensions import override

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import CookieJWTSyncAuth, request_jwt
from dmr.security.jwt.blocklist import JWTokenBlocklistSyncMixin
from dmr.security.jwt.views import CookieLogoutSyncController


class CookieJWTAuthWithBlocklist(
    JWTokenBlocklistSyncMixin,
    CookieJWTSyncAuth,
):
    """This class also checks that tokens are not blocklisted."""


cookie_blocklist_auth = CookieJWTAuthWithBlocklist()


class LogoutAndBlocklistController(
    CookieLogoutSyncController[PydanticSerializer],
):
    # Auth is required here: we can only blocklist a token we could read.
    # Which also means that this endpoint answers `401`
    # when the access token has already expired.
    auth = (cookie_blocklist_auth,)
    jwt_refresh_cookie_path = '/api/auth/refresh/'

    @override
    def revoke_tokens(self) -> None:
        # After this the access token is rejected by the auth above,
        # even though it is still a valid, non-expired token:
        cookie_blocklist_auth.blocklist(
            request_jwt(self.request, strict=True),
        )


# openapi: {"controller": "LogoutAndBlocklistController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
