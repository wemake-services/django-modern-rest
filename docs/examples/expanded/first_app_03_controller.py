import sys

import pydantic
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import HttpResponse
from django.urls import include, path

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

DATABASE = {
    '1': 'Alex',
    '2': 'Sasha',
}

# Configure Django settings
# For now, just leave it as is
# Real apps typically add INSTALLED_APPS and MIDDLEWARE. We will add it later
settings.configure(
    DEBUG=True,
    SECRET_KEY='your-secret-key-here',
    ROOT_URLCONF=__name__,
)


# Models for users
# This handles and verifies response to api/get_users/ endpoint
class UsersResponseModel(pydantic.BaseModel):
    users: dict


# Controller for users with pydantic serializer
class UsersController(Controller[PydanticSerializer]):
    def get(self) -> UsersResponseModel:
        return UsersResponseModel(users=DATABASE)


# Models for user
# Model for payload data for api/set_user endpoint
class UserCreateModel(pydantic.BaseModel):
    id: int
    name: str


# Mode for response of api/set_user
class UserCreateStatusModel(pydantic.BaseModel):
    status: bool
    message: str


# Controller for user
class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
):
    def post(self) -> UserCreateStatusModel:
        user_id = self.parsed_body.id
        name = self.parsed_body.name
        DATABASE[user_id] = name
        return UserCreateStatusModel(
            status=True, message=f'User with {user_id=} and {name=} created'
        )


user_router = Router(
    [
        path('set_user/', UserController.as_view(), name='user'),
    ],
    prefix='api/',
)

users_router = Router(
    [
        path('get_users/', UsersController.as_view(), name='users'),
    ],
    prefix='api/',
)

urlpatterns = [
    path('', lambda request: HttpResponse('Hello from Django Modern Rest!')),
    path(user_router.prefix, include((user_router.urls, 'your_app'))),
    path(users_router.prefix, include((users_router.urls, 'your_app'))),
]


if __name__ == '__main__':
    # This code passes all arguments from command line to Django.
    # For example, simple way to run code is python3 main.py runserver
    execute_from_command_line(sys.argv)
