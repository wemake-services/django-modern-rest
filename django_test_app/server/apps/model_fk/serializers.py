import datetime as dt
from typing import Annotated, TypeAlias, final

import pydantic

DatabaseId: TypeAlias = Annotated[int, pydantic.Field(gt=0)]


@final
class TagSchema(pydantic.BaseModel):
    name: str


@final
class RoleSchema(pydantic.BaseModel):
    name: str


class UserCreateSchema(pydantic.BaseModel):
    email: str
    role: RoleSchema
    tags: list[TagSchema]


@final
class UserSchema(UserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime
