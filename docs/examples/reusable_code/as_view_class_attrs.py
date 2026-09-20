from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path
from dmr.security.token import concrete_views
from dmr.security.token.app.models import Token

router = Router(
    'api/',
    [
        path(
            'auth/',
            # Both required fields, so there is no view class anywhere:
            concrete_views.ObtainTokenSyncController.as_view(
                serializer=PydanticSerializer,
                token_cls=Token,
            ),
            name='obtain_token',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]

# run: {"method": "post", "body": {"username": "test_user", "password": "password"}, "url": "/api/auth/", "populate_db": true, "use_urlpatterns": true}  # noqa: ERA001, E501
