from typing import final

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from server.apps.models_example.serializers import UserCreateSchema, UserSchema
from server.apps.models_example.services import user_create_service


@final
class UserCreateController(
    Body[UserCreateSchema],
    Controller[PydanticSerializer],
):
    def post(self) -> UserSchema:
        return UserSchema.model_validate(
            user_create_service(self.parsed_body),
            from_attributes=True,  # <- note
        )
