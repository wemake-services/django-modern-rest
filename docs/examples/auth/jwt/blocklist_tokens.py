from django.contrib.auth.models import User
from django.http import HttpRequest

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWTAsyncAuth, get_jwt
from dmr.security.jwt.blocklist import JWTokenBlocklistAsyncMixin


class AuthenticatedRequest(HttpRequest):
    user: User


class JWTAuthWithBlocklist(JWTokenBlocklistAsyncMixin, JWTAsyncAuth):
    """This class will also check that tokens are not blocklisted."""


jwt_blocklist_auth = JWTAuthWithBlocklist()


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedRequest
    auth = (jwt_blocklist_auth,)

    async def get(self) -> str:
        # Disable tokens for users with old domain emails
        if self.request.user.email.endswith('@old-domain.com'):
            await jwt_blocklist_auth.blocklist(get_jwt(self.request))
        return 'authed'
