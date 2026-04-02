from http import HTTPStatus
from typing import final

import msgspec
from django.http import HttpResponse
from typing_extensions import override

from dmr import Body, Controller, modify
from dmr.endpoint import Endpoint
from dmr.errors import ErrorType
from dmr.metadata import ResponseSpec
from dmr.plugins.msgspec import MsgspecSerializer
from server.apps.model_simple.serializers import UserCreateSchema, UserSchema
from server.apps.model_simple.services import (
    UniqueConstraintError,
    user_create_service,
    user_list_service,
)


@final
class UserController(Controller[MsgspecSerializer]):
    def get(self) -> list[UserSchema]:
        """List existing users."""
        return msgspec.convert(
            # FIXME: eagerly converting queryset to json is very dangerous
            list(user_list_service()),
            type=list[UserSchema],
            from_attributes=True,
        )

    @modify(
        extra_responses=[
            ResponseSpec(
                Controller.error_model,
                status_code=HTTPStatus.CONFLICT,
            ),
        ],
    )
    def post(self, parsed_body: Body[UserCreateSchema]) -> UserSchema:
        """Create new user."""
        return msgspec.convert(
            user_create_service(parsed_body),
            type=UserSchema,
            from_attributes=True,
        )

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[MsgspecSerializer],
        exc: Exception,
    ) -> HttpResponse:
        # Handle custom errors that can happen in this controller:
        if isinstance(exc, UniqueConstraintError):
            return self.to_error(
                self.format_error(
                    'User `email` and `customer_service_uid` must be unique',
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.CONFLICT,
            )
        # Handle default errors:
        return super().handle_error(endpoint, controller, exc)


# run: {"controller": "UserController", "method": "post", "url": "/api/users/", "body": {"email": "minimalistic@example.com", "customer_service_uid": "e87035e1-27a6-4e6b-a61a-d395bd4e221a"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "get", "url": "/api/users/", "populate_db": true}  # noqa: ERA001, E501
