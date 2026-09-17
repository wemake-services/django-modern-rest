from dmr import Controller, modify
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import Components, SecurityScheme
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import Router, path
from dmr.security.django_session import DjangoSessionSyncAuth


class UserController(Controller[MsgspecSerializer]):
    # Requests can also arrive through the API gateway,
    # it is an alternative to the auth of each endpoint:
    security = ({'gateway': []},)

    @modify(auth=[DjangoSessionSyncAuth()])
    def get(self) -> str:
        return 'get'

    # This endpoint is also called by other services in the mesh:
    @modify(security=[{'mesh': []}])
    def post(self) -> str:
        return 'post'


router = Router('api/', [path('user/', UserController.as_view())])

config = OpenAPIConfig(
    title='My awesome API',
    version='1.0.0',
    # Schemes used in `security` must be declared by hand:
    components=Components(
        security_schemes={
            'gateway': SecurityScheme(
                type='apiKey',
                name='X-Gateway-Key',
                security_scheme_in='header',
            ),
            'mesh': SecurityScheme(
                type='mutualTLS',
                description='Service mesh mTLS',
            ),
        },
    ),
)
schema = build_schema(router, config=config)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
