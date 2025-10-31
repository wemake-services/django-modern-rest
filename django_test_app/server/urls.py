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

from django.urls import include, path, re_path

from django_modern_rest.openapi import (
    OpenAPIConfig,
    openapi_spec,
)
from django_modern_rest.openapi.objects import (
    Contact,
    ExternalDocumentation,
    License,
    Server,
    Tag,
)
from django_modern_rest.openapi.renderers import (
    JsonRenderer,
    RedocRenderer,
    ScalarRenderer,
    SwaggerRenderer,
)
from django_modern_rest.routing import Router, compose_blueprints
from server.apps.models_example import urls as models_example_urls
from server.apps.rest import views as rest_views

router = Router([
    path(
        'model_examples/',
        include(
            (models_example_urls.router.urls, 'models_example'),
            namespace='model_examples',
        ),
    ),
    path(
        'user/',
        compose_blueprints(
            rest_views.UserCreateBlueprint,
            rest_views.UserListBlueprint,
        ).as_view(),
        name='users',
    ),
    path(
        'user/<int:user_id>',
        compose_blueprints(
            rest_views.UserReplaceBlueprint,
            rest_views.UserUpdateBlueprint,
        ).as_view(),
        name='user_update',
    ),
    re_path(
        r'user/direct/re/(\d+)',
        compose_blueprints(rest_views.UserUpdateBlueprint).as_view(),
        name='user_update_direct_re',
    ),
    path(
        'user/direct/<int:user_id>',
        compose_blueprints(rest_views.UserUpdateBlueprint).as_view(),
        name='user_update_direct',
    ),
    path(
        'headers',
        rest_views.ParseHeadersController.as_view(),
        name='parse_headers',
    ),
    path(
        'async_headers',
        rest_views.AsyncParseHeadersController.as_view(),
        name='async_parse_headers',
    ),
    path(
        'csrf-token',
        rest_views.CsrfTokenController.as_view(),
        name='csrf_token',
    ),
    path(
        'csrf-protected',
        rest_views.CsrfProtectedController.as_view(),
        name='csrf_test',
    ),
    path(
        'async-csrf-protected',
        rest_views.AsyncCsrfProtectedController.as_view(),
        name='async_csrf_test',
    ),
    path(
        'custom-header',
        rest_views.CustomHeaderController.as_view(),
        name='custom_header',
    ),
    path(
        'rate-limited',
        rest_views.RateLimitedController.as_view(),
        name='rate_limited',
    ),
    path(
        'request-id',
        rest_views.RequestIdController.as_view(),
        name='request_id',
    ),
    path(
        'login-required',
        rest_views.LoginRequiredController.as_view(),
        name='login_required',
    ),
])

urlpatterns = [
    path('api/', include((router.urls, 'server'), namespace='api')),
    path(
        'docs/',
        openapi_spec(
            router=router,
            renderers=[
                SwaggerRenderer(),
                JsonRenderer(),
                ScalarRenderer(),
                RedocRenderer(),
            ],
            config=OpenAPIConfig(
                title='Test API',
                version='1.0.0',
                summary='Test Summary',
                description='Test Description',
                terms_of_service='Test Terms of Service',
                contact=Contact(name='Test Contact', email='test@test.com'),
                license=License(name='Test License', identifier='license'),
                external_docs=ExternalDocumentation(
                    url='https://test.com',
                    description='Test External Documentation',
                ),
                servers=[Server(url='http://127.0.0.1:8000/api/')],
                tags=[
                    Tag(name='Test Tag', description='Tag Description'),
                    Tag(name='Test Tag 2', description='Tag 2 Description'),
                ],
            ),
        ),
    ),
]
