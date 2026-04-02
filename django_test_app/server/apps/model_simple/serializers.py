import datetime as dt
import uuid
from typing import Annotated, TypeAlias, final

import msgspec

DatabaseId: TypeAlias = Annotated[int, msgspec.Meta(gt=0)]


class UserCreateSchema(msgspec.Struct):
    email: str
    customer_service_uid: uuid.UUID


@final
class UserSchema(UserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime
