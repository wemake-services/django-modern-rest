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

from django.urls import include, path, re_path

from django_modern_rest import Router, compose_controllers
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
    ScalarRenderer,
    SwaggerRenderer,
)
from rest_app import views

router = Router([
    path(
        'user/',
        compose_controllers(
            views.UserCreateController,
            views.UserListController,
        ).as_view(),
        name='users',
    ),
    path(
        'user/<int:user_id>',
        compose_controllers(
            views.UserReplaceController,
            views.UserUpdateController,
        ).as_view(),
        name='user_update',
    ),
    re_path(
        r'user/direct/re/(\d+)',
        views.UserUpdateController.as_view(),
        name='user_update_direct_re',
    ),
    path(
        'user/direct/<int:user_id>',
        views.UserUpdateController.as_view(),
        name='user_update_direct',
    ),
    path(
        'headers',
        views.ParseHeadersController.as_view(),
        name='parse_headers',
    ),
    path(
        'async_headers',
        views.AsyncParseHeadersController.as_view(),
        name='async_parse_headers',
    ),
    path('csrf-token', views.CsrfTokenController.as_view(), name='csrf_token'),
    path(
        'csrf-protected',
        views.CsrfProtectedController.as_view(),
        name='csrf_test',
    ),
    path(
        'async-csrf-protected',
        views.AsyncCsrfProtectedController.as_view(),
        name='async_csrf_test',
    ),
    path(
        'custom-header',
        views.CustomHeaderController.as_view(),
        name='custom_header',
    ),
    path(
        'rate-limited',
        views.RateLimitedController.as_view(),
        name='rate_limited',
    ),
])

urlpatterns = [
    path('api/', include((router.urls, 'rest_app'), namespace='api')),
    path(
        'docs/',
        openapi_spec(
            router=router,
            renderers=[
                SwaggerRenderer(),
                JsonRenderer(),
                ScalarRenderer(),
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
                servers=[Server(url='https://test.com')],
                tags=[
                    Tag(name='Test Tag', description='Tag Description'),
                    Tag(name='Test Tag 2', description='Tag 2 Description'),
                ],
            ),
        ),
    ),
]
