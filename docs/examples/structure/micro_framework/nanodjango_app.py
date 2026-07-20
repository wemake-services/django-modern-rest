import secrets
import uuid

import pydantic
from django.urls import include
from nanodjango import Django

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView, SwaggerView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path

app = Django(
    # `dmr` must be in `INSTALLED_APPS` to serve its templates and statics:
    EXTRA_APPS=['dmr'],
    ALLOWED_HOSTS=['*'],
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

# `app.path()` is called as a function here, not as a decorator,
# because we mount whole url confs instead of single views:
app.path(router.prefix, include((router.urls, 'your_app'), namespace='api'))
app.path(
    'docs/',
    include(
        [
            path('openapi.json/', OpenAPIJsonView.as_view(schema)),
            path('swagger/', SwaggerView.as_view(schema)),
        ],
    ),
)

if __name__ == '__main__':
    # Use `python nanodjango_app.py` to run the example.
    # Then visit `http://localhost:8000/docs/swagger/` to view the docs.
    app.run()
