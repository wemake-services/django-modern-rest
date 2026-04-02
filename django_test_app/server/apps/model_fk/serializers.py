import datetime as dt
from typing import Annotated, TypeAlias, final

import msgspec

DatabaseId: TypeAlias = Annotated[int, msgspec.Meta(gt=0)]


@final
class TagSchema(msgspec.Struct):
    name: str


@final
class RoleSchema(msgspec.Struct):
    name: str


class UserCreateSchema(msgspec.Struct):
    email: str
    role: RoleSchema
    tags: list[TagSchema]


@final
class UserSchema(UserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime
