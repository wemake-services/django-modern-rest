from typing import final

import pydantic

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.jwt import JWTAsyncAuth, JWTSyncAuth


@final
class _UserOutput(pydantic.BaseModel):
    username: str
    email: str
    is_active: bool


@final
class ControllerWithJWTSyncAuth(Controller[PydanticSerializer]):
    auth = (JWTSyncAuth(),)

    def post(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )


@final
class ControllerWithJWTAsyncAuth(Controller[PydanticSerializer]):
    auth = (JWTAsyncAuth(),)

    async def post(self) -> _UserOutput:
        return _UserOutput.model_validate(
            self.request.user,
            from_attributes=True,
        )
