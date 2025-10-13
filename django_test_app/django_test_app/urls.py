"""
URL configuration for django_test_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path

from django_modern_rest import Router, compose_controllers
from django_modern_rest.openapi import (
    JsonRenderer,
    OpenAPIConfig,
    OpenAPISetup,
    SwaggerRenderer,
)
from rest_app.views import (
    UserCreateController,
    UserListController,
    UserReplaceController,
    UserUpdateController,
)

router = Router([
    path(
        'user/',
        compose_controllers(UserCreateController, UserListController).as_view(),
        name='users',
    ),
    path(
        'user/<int:user_id>',
        compose_controllers(
            UserReplaceController,
            UserUpdateController,
        ).as_view(),
        name='user_update',
    ),
    path(
        'user/direct/<int:user_id>',
        UserUpdateController.as_view(),
        name='user_update_direct',
    ),
])

urlpatterns = [
    path('api/', include((router.urls, 'rest_app'), namespace='api')),
    path(
        'docs/',
        include(
            OpenAPISetup(
                router=router,
                renderers=[
                    SwaggerRenderer(),
                    JsonRenderer(),
                ],
                config=OpenAPIConfig(
                    title='Test API',
                    version='1.0.0',
                ),
            ).urls(),
            namespace='docs',
        ),
    ),
]
