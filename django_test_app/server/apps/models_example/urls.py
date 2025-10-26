from django_modern_rest import Router, path
from server.apps.models_example import views

router = Router([
    path(
        'user',
        views.UserCreateController.as_view(),
        name='user_model_create',
    ),
])
