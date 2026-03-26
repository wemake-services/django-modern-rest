import secrets
import sys
import uuid

import pydantic
from django.conf import settings
from django.core.management import execute_from_command_line
from django.urls import include

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, SwaggerView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path

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


class UserController(Controller[PydanticSerializer]):
    async def post(
        self,
        parsed_body: Body[UserCreateModel],
    ) -> UserResponseModel:
        return UserResponseModel(uid=uuid.uuid4(), email=parsed_body.email)


router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)
schema = build_schema(router)

urlpatterns = [
    path(router.prefix, include((router.urls, 'your_app'), namespace='api')),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
]

if __name__ == '__main__':
    # Use `python THIS_FILE_NAME.py runserver` to run the example.
    # Then visit `http://localhost:8000/docs/swagger` to view the docs.
    execute_from_command_line(sys.argv)

# run: {"controller": "UserController", "method": "post", "body": {"email": "djangomodernrest@wemake.services"}, "url": "/api/user/", "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001, E501
