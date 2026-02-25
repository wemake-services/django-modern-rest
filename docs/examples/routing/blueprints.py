from django.urls import include, path

from dmr.routing import Router, compose_blueprints
from examples.using_controller.blueprints import (
    UserCreateBlueprint,
    UserListBlueprint,
)

router = Router(
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
    prefix='api/',
)

urlpatterns = [
    path(router.prefix, include((router.urls, 'server'), namespace='api')),
]
