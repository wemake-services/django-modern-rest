# needs for run example
from .pydantic_controller import UserController  # noqa: I001, WPS300

from django.urls import include, path

from django_modern_rest.routing import Router


# Router is just a collection of regular Django urls:
router = Router([
    path(
        'user/',
        UserController.as_view(),
        name='users',
    ),
])

# Just a regular `urlpatterns` definition.
urlpatterns = [
    path('api/', include((router.urls, 'rest_app'), namespace='api')),
]

# run: {"controller": "UserController", "method": "post", "body": {"email": "user@wms.org"}, "headers": {"X-API-Consumer": "my-api"}, "url": "/api/user/"}  # noqa: ERA001, E501
