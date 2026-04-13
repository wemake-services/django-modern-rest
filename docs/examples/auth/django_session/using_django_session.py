from django.contrib.auth.models import User

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.django_session import DjangoSessionSyncAuth


class APIController(Controller[PydanticSerializer]):
    request: AuthenticatedHttpRequest[User]
    auth = (DjangoSessionSyncAuth(),)

    def get(self) -> str:
        # Let's test that `User` has the correct type:
        assert self.request.user.username
        return 'authed'
