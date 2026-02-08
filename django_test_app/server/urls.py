"""
URL configuration for django_test_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', rest_views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path

from django_modern_rest.routing import Router
from server.apps.controllers import urls as controllers_urls
from server.apps.django_session_auth import urls as django_session_auth_urls
from server.apps.jwt_auth import urls as jwt_auth_urls
from server.apps.middlewares import urls as middleware_urls
from server.apps.models_example import urls as models_example_urls
from server.apps.negotiations import urls as negotiations_urls
from server.apps.openapi.urls import build_spec

router = Router([
    path(
        'model-examples/',
        include(
            (models_example_urls.router.urls, 'models_example'),
            namespace='model_examples',
        ),
    ),
    path(
        'middlewares/',
        include(
            (middleware_urls.router.urls, 'middlewares'),
            namespace='middlewares',
        ),
    ),
    path(
        'controllers/',
        include(
            (controllers_urls.router.urls, 'controllers'),
            namespace='controllers',
        ),
    ),
    path(
        'negotiations/',
        include(
            (negotiations_urls.router.urls, 'negotiations'),
            namespace='negotiations',
        ),
    ),
    path(
        'jwt-auth/',
        include(
            (jwt_auth_urls.router.urls, 'jwt_auth'),
            namespace='jwt_auth',
        ),
    ),
    path(
        'django-session-auth/',
        include(
            (django_session_auth_urls.router.urls, 'django_session_auth'),
            namespace='django_session_auth',
        ),
    ),
])

urlpatterns = [
    path('api/', include((router.urls, 'server'), namespace='api')),
    path('docs/', build_spec(router)),
]
