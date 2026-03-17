from django.urls import include

from dmr.routing import Router, compose_blueprints, path
from examples.using_controller.blueprints import (
    UserCreateBlueprint,
    UserListBlueprint,
)

router = Router(
    'api/',
    [
        path(
            'user/',
            compose_blueprints(
                UserCreateBlueprint,
                UserListBlueprint,
                # Can compose as many blueprints as you need!
            ).as_view(),
            name='users',
        ),
    ],
)

urlpatterns = [
    path(router.prefix, include((router.urls, 'server'), namespace='api')),
]

# run: {"method": "get", "url": "/api/user/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"method": "post", "url": "/api/user/", "body": {"email": "some@example.com", "age": 20}, "use_urlpatterns": true}  # noqa: ERA001, E501
