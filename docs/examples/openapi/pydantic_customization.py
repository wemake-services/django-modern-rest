import pydantic


class UserModel(pydantic.BaseModel):
    email: str = pydantic.Field(
        json_schema_extra={'example': 'user@example.com'},
    )
