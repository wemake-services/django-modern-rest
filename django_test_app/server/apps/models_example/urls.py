from django.urls import path

from django_modern_rest.routing import Router
from server.apps.models_example import views

router = Router([
    path(
        'user',
        views.UserCreateController.as_view(),
        name='user_model_create',
    ),
])
