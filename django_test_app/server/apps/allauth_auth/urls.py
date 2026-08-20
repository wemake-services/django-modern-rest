import json

from allauth.headless.account.views import LoginView, SessionView
from allauth.headless.constants import Client

from dmr.openapi import load_schema
from dmr.openapi.objects import PathItem
from dmr.routing import Router, external_path, path
from server.apps.allauth_auth import views

router = Router(
    'allauth-auth/',
    urls=[
        # These two are served by `django-allauth` itself.
        # We only pull them into our own routing and OpenAPI schema:
        external_path(
            'login/',
            LoginView.as_api_view(client=Client.APP),
            name='login',
            # Deliberately hidden from our schema. `django-allauth` answers
            # `500` to any JSON body that is not an object, so publishing it
            # would put a known upstream crash into our own contract.
            # `views.LOGIN_OPENAPI` describes it for the docs meanwhile.
            openapi=None,
        ),
        external_path(
            'session/',
            SessionView.as_api_view(client=Client.APP),
            name='current_session',
            openapi=load_schema(json.loads(views.SESSION_OPENAPI), PathItem),
        ),
        # And these two are ours, protected by the token issued above:
        path(
            'user-sync/',
            views.ControllerWithSessionTokenSyncAuth.as_view(),
            name='user_sync',
        ),
        path(
            'user-async/',
            views.ControllerWithSessionTokenAsyncAuth.as_view(),
            name='user_async',
        ),
    ],
)
