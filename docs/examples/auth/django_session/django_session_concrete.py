from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.django_session import concrete_views

router = Router(
    'api/',
    [
        # You can also use `DjangoSessionAsyncController` if needed:
        path(
            'auth/',
            concrete_views.DjangoSessionSyncController.as_view(
                serializer=PydanticSerializer,
            ),
            name='session_login',
        ),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path(
        'docs/openapi.json/',
        OpenAPIJsonView.as_view(build_schema(router)),
        name='openapi_json',
    ),
]

# run: {"method": "post", "url": "/api/auth/", "body": {"username": "test_user", "password": "password"}, "curl_args": ["-D", "-"], "populate_db": true, "use_urlpatterns": true}  # noqa: ERA001, E501
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
