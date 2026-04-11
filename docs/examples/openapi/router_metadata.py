from dmr.routing import Router, path
from examples.getting_started.msgspec_controller import UserController

api_routes = [
    Router(
        'api/v1/users/',
        [
            path('', UserController.as_view()),
            path('<int:user_id>/', UserController.as_view()),
        ],
        tags=['users'],  # All endpoints tagged as 'users'
        deprecated=True,  # All endpoints are deprecated
    ),
]
