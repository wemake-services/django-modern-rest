from dmr.routing import Router, path
from server.apps.etag.views import ConditionalETagController

router = Router(
    'etag/',
    [
        path(
            '<int:user_id>/',
            ConditionalETagController.as_view(),
            name='user',
        ),
    ],
)

urlpatterns = router.urls
