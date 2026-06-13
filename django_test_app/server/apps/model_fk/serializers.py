import datetime as dt
from typing import Annotated, TypeAlias, final

import pydantic

DatabaseId: TypeAlias = Annotated[int, pydantic.Field(gt=0)]


@final
class PageQuery(pydantic.BaseModel):
    page_size: int = pydantic.Field(default=10, ge=1, le=100)
    page: int = pydantic.Field(default=1, ge=1)

    model_config = pydantic.ConfigDict(extra='forbid')


@final
class TagSchema(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=100)


@final
class RoleSchema(pydantic.BaseModel):
    name: str = pydantic.Field(max_length=100)


class UserCreateSchema(pydantic.BaseModel):
    email: str
    role: RoleSchema
    tags: list[TagSchema]


@final
class UserSchema(UserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime
