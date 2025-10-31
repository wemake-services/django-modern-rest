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
from server.apps.middlewares import urls as middleware_urls
from server.apps.models_example import urls as models_example_urls
from server.apps.openapi.urls import build_spec

router = Router([
    path(
        'model_examples/',
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
])

urlpatterns = [
    path('api/', include((router.urls, 'server'), namespace='api')),
    path('docs/', build_spec(router)),
]
