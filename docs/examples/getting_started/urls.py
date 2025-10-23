from .views import UserController  # noqa: I001

from django.urls import include, path

from django_modern_rest import Router


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
