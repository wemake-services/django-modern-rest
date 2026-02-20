from http import HTTPStatus
from typing import final

from dmr import APIError, Body, Controller, modify
from dmr.errors import ErrorModel, ErrorType
from dmr.metadata import ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from server.apps.models_example.serializers import (
    UserCreateSchema,
    UserSchema,
)
from server.apps.models_example.services import (
    UniqueEmailError,
    user_create_service,
)


@final
class UserCreateController(
    Body[UserCreateSchema],
    Controller[PydanticSerializer],
):
    @modify(
        extra_responses=[
            ResponseSpec(
                ErrorModel,
                status_code=HTTPStatus.CONFLICT,
            ),
        ],
    )
    def post(self) -> UserSchema:
        try:
            user = user_create_service(self.parsed_body)
        except UniqueEmailError:
            raise APIError(
                self.format_error(
                    'User email must be unique',
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.CONFLICT,
            ) from None
        return UserSchema(
            id=user.pk,
            created_at=user.created_at,
            email=user.email,
            role=self.parsed_body.role,
            tags=self.parsed_body.tags,
        )
