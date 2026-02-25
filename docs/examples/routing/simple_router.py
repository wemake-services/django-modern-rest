from examples.using_controller import simple_routing_controllers as views  # noqa: I001

from dmr.routing import Router, path

router = Router(
    [
        path('users/', views.UserList.as_view()),
        path('posts/', views.PostList.as_view()),
        path('users/<int:id>/', views.UserDetail.as_view()),
    ],
    prefix='api/v1',
)
