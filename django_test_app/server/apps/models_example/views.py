from http import HTTPStatus
from typing import final

from django.http import HttpResponse
from typing_extensions import override

from dmr import Body, Controller, modify
from dmr.endpoint import Endpoint
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
class UserCreateController(Controller[PydanticSerializer]):
    @modify(
        extra_responses=[
            ResponseSpec(
                ErrorModel,
                status_code=HTTPStatus.CONFLICT,
            ),
        ],
    )
    def post(self, parsed_body: Body[UserCreateSchema]) -> UserSchema:
        user = user_create_service(parsed_body)
        return UserSchema(
            id=user.pk,
            created_at=user.created_at,
            email=user.email,
            role=parsed_body.role,
            tags=parsed_body.tags,
        )

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        # Handle custom errors that can happen in this controller:
        if isinstance(exc, UniqueEmailError):
            return self.to_error(
                self.format_error(
                    'User email must be unique',
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.CONFLICT,
            )
        # Handle default errors:
        return super().handle_error(endpoint, controller, exc)
