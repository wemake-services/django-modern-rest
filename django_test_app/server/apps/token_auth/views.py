from typing import final

import pydantic

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
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
