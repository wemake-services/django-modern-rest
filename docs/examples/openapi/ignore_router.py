from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

private_router = Router(
    'private/',
    [
        path('users/', UserController.as_view()),
    ],
    ignore_from_spec=True,
)

router = Router(
    'api/',
    [
        path('users/', UserController.as_view()),
    ],
)
router.include(private_router)

schema = build_schema(router)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema)),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
