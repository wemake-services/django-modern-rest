import secrets
import sys
import uuid

import pydantic
from django.conf import settings
from django.core.management import execute_from_command_line
from django.urls import include, path

from dmr import Body, Controller
from dmr.openapi import OpenAPIConfig, openapi_spec
from dmr.openapi.objects import Server
from dmr.openapi.renderers import JsonRenderer, SwaggerRenderer
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router

if not settings.configured:
    settings.configure(
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS='*',
        DEBUG=True,
        INSTALLED_APPS=['dmr', 'django.contrib.staticfiles'],
        STATIC_URL='/static/',
        STATICFILES_FINDERS=[
            'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        ],
        TEMPLATES=[
            {
                'APP_DIRS': True,
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
            },
        ],
        # Secret key for tests, will be new on each run,
        # in production it must be the same token, kept in secret:
        SECRET_KEY=secrets.token_hex(),
    )


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserResponseModel(UserCreateModel):
    uid: uuid.UUID


class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
):
    async def post(self) -> UserResponseModel:
        return UserResponseModel(uid=uuid.uuid4(), email=self.parsed_body.email)


router = Router([
    path('user/', UserController.as_view(), name='users'),
])
urlpatterns = [
    path('api/', include((router.urls, 'your_app'), namespace='api')),
    path(
        'docs/',
        openapi_spec(
            router,
            renderers=[JsonRenderer(), SwaggerRenderer()],
            config=OpenAPIConfig(
                title='django-modern-rest',
                version='0.1.0',
                servers=[Server(url='/api')],
            ),
        ),
    ),
]

if __name__ == '__main__':
    # Use `python THIS_FILE_NAME.py runserver` to run the example.
    # Then visit `http://localhost:8000/docs/swagger` to view the docs.
    execute_from_command_line(sys.argv)

# run: {"controller": "UserController", "method": "post", "body": {"email": "djangomodernrest@wms.org"}, "url": "/api/user/"}  # noqa: ERA001, E501
