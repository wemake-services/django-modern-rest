from django.urls import path, re_path

from django_modern_rest.routing import Router, compose_blueprints
from server.apps.controllers import views

router = Router([
    path(
        'user/',
        compose_blueprints(
            views.UserCreateBlueprint,
            views.UserListBlueprint,
        ).as_view(),
        name='users',
    ),
    path(
        'user/<int:user_id>',
        compose_blueprints(
            views.UserReplaceBlueprint,
            views.UserUpdateBlueprint,
        ).as_view(),
        name='user_update',
    ),
    re_path(
        r'user/direct/re/(?P<user_id>\d+)$',
        compose_blueprints(views.UserUpdateBlueprint).as_view(),
        name='user_update_direct_re',
    ),
    path(
        'user/direct/<int:user_id>',
        compose_blueprints(views.UserUpdateBlueprint).as_view(),
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
    path(
        'constrained-user',
        views.ConstrainedUserController.as_view(),
        name='constrained_user_create',
    ),
])
