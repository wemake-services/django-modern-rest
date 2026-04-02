from http import HTTPStatus
from typing import final

from django.http import HttpResponse
from typing_extensions import override

from dmr import Body, Controller, modify
from dmr.endpoint import Endpoint
from dmr.errors import ErrorType
from dmr.metadata import ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from server.apps.model_fk.implemented import HasContainer
from server.apps.model_fk.serializers import UserCreateSchema, UserSchema
from server.apps.model_fk.services import (
    UniqueConstraintError,
    UserCreate,
    UserList,
)


@final
class UserController(HasContainer, Controller[PydanticSerializer]):
    def get(self) -> list[UserSchema]:
        """List existing users."""
        return self.resolve(UserList)()

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
        return self.resolve(UserCreate)(parsed_body)

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        # Handle custom errors that can happen in this controller:
        if isinstance(exc, UniqueConstraintError):
            return self.to_error(
                self.format_error(
                    'User `email` must be unique',
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.CONFLICT,
            )
        # Handle default errors:
        return super().handle_error(endpoint, controller, exc)


# run: {"controller": "UserController", "method": "post", "url": "/api/users/", "body": {"email": "test@example.com", "role": {"name": "admin"}, "tags": [{"name": "paid"}]}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "get", "url": "/api/users/", "populate_db": true}  # noqa: ERA001, E501
