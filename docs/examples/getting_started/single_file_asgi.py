import uuid

import pydantic
from django.conf import settings
from django.core.handlers import asgi
from django.urls import include, path

from django_modern_rest import Body, Controller, Headers, Router
from django_modern_rest.plugins.pydantic import PydanticSerializer

if not settings.configured:
    settings.configure(
        # Keep it as is
        ROOT_URLCONF=__name__,
        # Required options but feel free to configure as you like
        DMR_SETTINGS={},
        ALLOWED_HOSTS='*',
        DEBUG=True,
    )

app = asgi.ASGIHandler()


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


class HeaderModel(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')


class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
    Headers[HeaderModel],
):
    async def post(self) -> UserModel:
        assert self.parsed_headers.token == 'secret!'
        return UserModel(uid=uuid.uuid4(), email=self.parsed_body.email)


router = Router([
    path('user/', UserController.as_view(), name='users'),
])
urlpatterns = [
    path('api/', include((router.urls, 'your_app'), namespace='api')),
]

# run: {"controller": "UserController", "method": "post", "body": {"email": "djangomodernrest@wms.org"}, "headers": {"X-API-Token": "secret!"}, "url": "/api/user/"}  # noqa: ERA001, E501
