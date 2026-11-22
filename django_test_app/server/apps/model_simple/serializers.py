import datetime as dt
import uuid
from typing import Annotated, TypeAlias, final

import pydantic

DatabaseId: TypeAlias = Annotated[int, pydantic.Field(gt=0)]


class SimpleUserCreateSchema(pydantic.BaseModel):
    # The database column is limited to 254 characters:
    email: str = pydantic.Field(max_length=254)  # noqa: WPS432
    customer_service_uid: uuid.UUID


@final
class SimpleUserSchema(SimpleUserCreateSchema):
    id: DatabaseId
    created_at: dt.datetime
