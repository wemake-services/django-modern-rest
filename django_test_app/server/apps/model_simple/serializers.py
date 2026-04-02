import datetime as dt
import uuid
from typing import Annotated, TypeAlias, final

import pydantic

DatabaseId: TypeAlias = Annotated[int, pydantic.Field(gt=0)]


class SimpleUserCreateSchema(pydantic.BaseModel):
    email: str
    customer_service_uid: uuid.UUID


@final
class SimpleUserSchema(SimpleUserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime
