import datetime as dt
from typing import final

import pydantic


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
    id: int
    created_at: dt.datetime
