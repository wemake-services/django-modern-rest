from examples.using_controller import simple_routing_controllers as views  # noqa: I001

from django_modern_rest.routing import Router, path

router = Router(
    [
        path('api/v1/users/', views.UserList.as_view()),
        path('api/v1/posts/', views.PostList.as_view()),
        path('api/v1/users/<int:id>/', views.UserDetail.as_view()),
    ],
)
