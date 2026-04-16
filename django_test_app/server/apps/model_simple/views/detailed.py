from http import HTTPStatus
from typing import final

from django.http import HttpResponse
from typing_extensions import override

from dmr import Body, Controller, modify
from dmr.endpoint import Endpoint
from dmr.errors import ErrorType
from dmr.metadata import ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from server.apps.model_simple.serializers import (
    SimpleUserCreateSchema,
    SimpleUserSchema,
)
from server.apps.model_simple.services import (
    UniqueConstraintError,
    user_create_service,
    user_list_service,
)


@final
class UserController(Controller[PydanticSerializer]):
    def get(self) -> list[SimpleUserSchema]:
        """List existing users."""
        return [
            SimpleUserSchema(
                id=user.pk,
                email=user.email,
                customer_service_uid=user.customer_service_uid,
                created_at=user.created_at,
            )
            for user in user_list_service()
        ]

    @modify(
        extra_responses=[
            ResponseSpec(
                Controller.error_model,
                status_code=HTTPStatus.CONFLICT,
            ),
        ],
    )
    def post(
        self,
        parsed_body: Body[SimpleUserCreateSchema],
    ) -> SimpleUserSchema:
        """Create new user."""
        user = user_create_service(parsed_body)
        return SimpleUserSchema(
            id=user.pk,
            email=user.email,
            customer_service_uid=user.customer_service_uid,
            created_at=user.created_at,
        )

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
                    'User `email` and `customer_service_uid` must be unique',
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.CONFLICT,
            )
        # Handle default errors:
        return super().handle_error(endpoint, controller, exc)


# run: {"controller": "UserController", "method": "post", "url": "/api/users/", "body": {"email": "detailed@example.com", "customer_service_uid": "616d51f2-2c31-4b04-8034-2f59eae042db"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "get", "url": "/api/users/", "populate_db": true}  # noqa: ERA001, E501
