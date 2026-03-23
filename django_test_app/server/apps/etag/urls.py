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


# run: {"controller": "ConditionalETagController", "method": "get", "url": "/1/", "use_urlpatterns": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "ConditionalETagController", "method": "get", "url": "/1/", "use_urlpatterns": true, "headers": {"If-None-Match": "\"user-1-2026-03-23T12:30:00+00:00\""}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "ConditionalETagController", "method": "get", "url": "/2/", "use_urlpatterns": true, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
