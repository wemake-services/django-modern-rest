from typing import final

import pydantic

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from server.apps.token_custom_user.auth import (
    HeaderApiTokenAsyncAuth,
    HeaderApiTokenSyncAuth,
)


@final
class _ApiUserInfo(pydantic.BaseModel):
    username: str
    is_active: bool


@final
class ControllerWithApiTokenSyncAuth(Controller[PydanticSerializer]):
    auth = (HeaderApiTokenSyncAuth(update_last_used=True),)

    def get(self) -> _ApiUserInfo:
        return _ApiUserInfo.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithApiTokenAsyncAuth(Controller[PydanticSerializer]):
    auth = (HeaderApiTokenAsyncAuth(update_last_used=True),)

    async def get(self) -> _ApiUserInfo:
        return _ApiUserInfo.model_validate(
            self.request.user,
            from_attributes=True,
        )
