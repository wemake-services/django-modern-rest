from django.contrib.auth.models import User
from myapp.models import ProjectToken  # type: ignore[import-not-found]

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AuthenticatedHttpRequest
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.security.token.logic import token_create


class IssueProjectTokenController(Controller[PydanticSerializer]):
    """Issue a token using the custom ProjectToken model."""

    request: AuthenticatedHttpRequest[User]
    auth = (DjangoSessionSyncAuth(),)

    def post(self) -> None:
        token, raw_token = token_create(  # noqa: RUF059
            user=self.request.user,
            name='project-api-key',
            token_model=ProjectToken,
        )
        # raw_token is only available here - return it to the client now.
        # Only its hash is stored; it cannot be recovered after this point.
