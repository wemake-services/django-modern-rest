import secrets
import uuid

import django
import pydantic
from django.conf import settings
from django.core.handlers.asgi import ASGIHandler

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import path

if not settings.configured:
    settings.configure(
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS='*',
        DEBUG=True,
        INSTALLED_APPS=['dmr'],
        # Secret key for tests, will be new on each run,
        # in production it must be the same token, kept in secret:
        SECRET_KEY=secrets.token_hex(),
    )
    django.setup()


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserResponseModel(UserCreateModel):
    uid: uuid.UUID


class UserController(Controller[PydanticSerializer]):
    async def post(
        self,
        parsed_body: Body[UserCreateModel],
    ) -> UserResponseModel:
        return UserResponseModel(uid=uuid.uuid4(), email=parsed_body.email)


urlpatterns = [
    path('user/', UserController.as_view(), name='users'),
]

# Use `uvicorn udjango_style_asgi:app --reload` to run the example.
app = ASGIHandler()
