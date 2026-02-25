import sys
import uuid
import secrets

import pydantic
from django.conf import settings
from django.core.handlers import asgi
from django.core.management import execute_from_command_line
from django.urls import include, path

from dmr import Body, Controller, Headers
from dmr.openapi import openapi_spec
from dmr.openapi.renderers import JsonRenderer, SwaggerRenderer
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

if not settings.configured:
    settings.configure(
        # Keep it as is
        ROOT_URLCONF=__name__,
        # Required options but feel free to configure as you like
        DMR_SETTINGS={},
        ALLOWED_HOSTS='*',
        DEBUG=True,
        INSTALLED_APPS=['dmr'],
        # Secret key for tests, will be new on each run,
        # in production it must be the same token, kept in secret:
        SECRET_KEY=secrets.token_hex(),
    )

app = asgi.ASGIHandler()


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class HeaderModel(pydantic.BaseModel):
    consumer: str = pydantic.Field(alias='X-API-Consumer')


class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    async def post(self) -> UserModel:
        assert self.parsed_headers.consumer == 'my-api'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)


router = Router([
    path('user/', UserController.as_view(), name='users'),
])
urlpatterns = [
    path('api/', include((router.urls, 'your_app'), namespace='api')),
    path(
        'docs/',
        openapi_spec(router, renderers=[JsonRenderer(), SwaggerRenderer()]),
    ),
]

if __name__ == '__main__':
    # Use `python THIS_FILE_NAME.py runserver` to run the example.
    # Then visit `http://localhost:8000/docs/swagger` to view the docs.
    execute_from_command_line(sys.argv)

# run: {"controller": "UserController", "method": "post", "body": {"email": "djangomodernrest@wms.org"}, "headers": {"X-API-Consumer": "my-api"}, "url": "/api/user/"}  # noqa: ERA001, E501
