from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import (
    Components,
    MediaType,
    OAuthFlow,
    OAuthFlows,
    Schema,
    SecurityScheme,
    Server,
    Tag,
)
from dmr.openapi.views import OpenAPIJsonView, SwaggerView
from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

config = OpenAPIConfig(
    title='My awesome API',
    version='1.0.0',
    openapi_version='3.2.0',
    # `$self` gives the document its own URI, references resolve against it:
    self_uri='https://example.com/docs/openapi.json/',
    # Servers can now be named:
    servers=[Server(url='https://prod.example.com', name='production')],
    # Tags can be nested and classified:
    tags=[
        Tag(name='public', summary='Public', kind='audience'),
        Tag(name='users', summary='Users', parent='public', kind='nav'),
    ],
    components=Components(
        # Media types are reusable components now,
        # refer to them as `#/components/mediaTypes/Problem`:
        media_types={
            'Problem': MediaType(
                description='RFC9457 problem details',
                schema=Schema(ref='#/components/schemas/ProblemDetails'),
            ),
        },
        security_schemes={
            'device': SecurityScheme(
                type='oauth2',
                # Schemes can be deprecated and point at their metadata:
                deprecated=True,
                oauth2_metadata_url='https://example.com/.well-known/oauth',
                flows=OAuthFlows(
                    # The device authorization grant, RFC8628:
                    device_authorization=OAuthFlow(
                        device_authorization_url='https://example.com/device/',
                        token_url='https://example.com/token/',
                        scopes={'read': 'Read everything'},
                    ),
                ),
            ),
        },
    ),
)
schema = build_schema(router, config=config)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path('docs/openapi.json/', OpenAPIJsonView.as_view(schema), name='openapi'),
    path('docs/swagger/', SwaggerView.as_view(schema), name='swagger'),
]

# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
