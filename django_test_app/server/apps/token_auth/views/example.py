from typing import final

import pydantic

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.token import HeaderTokenSyncAuth
from server.apps.token_auth.auth import HeaderCustomTokenSyncAuth


@final
class _TokenOwner(pydantic.BaseModel):
    username: str
    email: str
    is_active: bool


@final
class ControllerWithTokenSyncAuth(Controller[PydanticSerializer]):
    auth = (HeaderCustomTokenSyncAuth(),)

    def post(self) -> _TokenOwner:
        return _TokenOwner.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithDefaultTokenSyncAuth(Controller[PydanticSerializer]):
    """Reads tokens of the bundled model, every setting at its default."""

    auth = (HeaderTokenSyncAuth(),)

    def get(self) -> _TokenOwner:
        return _TokenOwner.model_validate(
            self.request.user,
            from_attributes=True,
        )
