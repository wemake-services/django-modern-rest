import uuid
from typing import final

import pydantic

from django_modern_rest import (  # noqa: WPS235
    Blueprint,
    Body,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _UserInput(pydantic.BaseModel):
    email: str
    age: int


@final
class _UserOutput(_UserInput):
    uid: uuid.UUID


@final
class UserCreateBlueprint(
    Body[_UserInput],  # <- needs a request body
    Blueprint[PydanticSerializer],
):
    def post(self) -> _UserOutput:
        return _UserOutput(
            uid=uuid.uuid4(),
            email=self.parsed_body.email,
            age=self.parsed_body.age,
        )


@final
class UserListBlueprint(
    # Does not need a request body.
    Blueprint[PydanticSerializer],
):
    def get(self) -> list[_UserInput]:
        return [
            _UserInput(email='first@example.org', age=1),
            _UserInput(email='second@example.org', age=2),
        ]
