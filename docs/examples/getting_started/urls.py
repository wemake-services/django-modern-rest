from django.urls import include

# Our `path` is an optimized drop-in replacement of `django.urls.path`:
from dmr.routing import Router, path
from examples.getting_started.pydantic_controller import UserController

# Router is just a collection of regular Django urls:
router = Router(
    'api/',
    [
        path(
            'user/',
            UserController.as_view(),
            name='users',
        ),
    ],
)

# Just a regular `urlpatterns` definition, Django-style:
urlpatterns = [
    path(router.prefix, include((router.urls, 'rest_app'), namespace='api')),
]

# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "headers": {"X-API-Consumer": "my-api"}, "url": "/api/user/"}  # noqa: ERA001, E501
