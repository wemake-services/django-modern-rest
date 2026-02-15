from http import HTTPStatus
from typing import final

from django_modern_rest import APIError, Body, Controller, modify
from django_modern_rest.errors import ErrorType
from django_modern_rest.plugins.pydantic import PydanticSerializer
from server.apps.models_example.serializers import UserCreateSchema, UserSchema
from server.apps.models_example.services import (
    UniqueEmailError,
    user_create_service,
)


@final
class UserCreateController(
    Body[UserCreateSchema],
    Controller[PydanticSerializer],
):
    @modify(validate_responses=False)
    def post(self) -> UserSchema:
        try:
            return UserSchema.model_validate(
                user_create_service(self.parsed_body),
                from_attributes=True,  # <- note
            )
        except UniqueEmailError:
            raise APIError(
                self.format_error(
                    'User email must be unique',
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.CONFLICT,
            ) from None
