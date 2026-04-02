import datetime as dt
import uuid
from typing import Annotated, TypeAlias, final

import pydantic

DatabaseId: TypeAlias = Annotated[int, pydantic.Field(gt=0)]


class UserCreateSchema(pydantic.BaseModel):
    email: str
    customer_service_uid: uuid.UUID

    model_config = pydantic.ConfigDict(title='SimpleUserCreateSchema')


@final
class UserSchema(UserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime

    model_config = pydantic.ConfigDict(title='SimpleUserSchema')
