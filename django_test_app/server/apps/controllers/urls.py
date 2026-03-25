from django.urls import re_path

from dmr.routing import Router, path
from server.apps.controllers import views

router = Router(
    'controllers/',
    [
        path(
            'user/',
            views.UsersController.as_view(),
            name='users',
        ),
        path(
            'user/<int:user_id>/',
            views.UserUpdateController.as_view(),
            name='user_update',
        ),
        re_path(
            r'user/direct/re/(?P<user_id>\d+)/$',
            views.UserUpdateController.as_view(),
            name='user_update_direct_re',
        ),
        path(
            'user/direct/<int:user_id>/',
            views.UserUpdateController.as_view(),
            name='user_update_direct',
        ),
        path(
            'headers/',
            views.ParseHeadersController.as_view(),
            name='parse_headers',
        ),
        path(
            'async_headers/',
            views.AsyncParseHeadersController.as_view(),
            name='async_parse_headers',
        ),
        path(
            'constrained-user/',
            views.ConstrainedUserController.as_view(),
            name='constrained_user_create',
        ),
    ],
)
