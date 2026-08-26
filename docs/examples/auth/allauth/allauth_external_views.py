from allauth.headless.account.views import LoginView, SessionView
from allauth.headless.constants import Client

from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, external_path, path

# `LOGIN_PATH_ITEM` and `SESSION_PATH_ITEM` describe what these two
# `django-allauth` views answer, taken from its own specification:
# https://docs.allauth.org/en/latest/headless/openapi-specification/
from examples.auth.allauth.allauth_openapi import (
    LOGIN_PATH_ITEM,
    SESSION_PATH_ITEM,
)

router = Router(
    'auth/',
    urls=[
        # `django-allauth` serves these two itself,
        # `client=Client.APP` is what makes it hand out session tokens:
        external_path(
            'login/',
            LoginView.as_api_view(client=Client.APP),
            name='login',
            openapi=LOGIN_PATH_ITEM,
        ),
        external_path(
            'session/',
            SessionView.as_api_view(client=Client.APP),
            name='current_session',
            openapi=SESSION_PATH_ITEM,
        ),
    ],
)
schema = build_schema(router)

urlpatterns = [
    router.to_urlpatterns(namespace='auth'),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]


# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
