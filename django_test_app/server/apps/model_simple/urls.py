from dmr.routing import Router, path
from server.apps.model_simple.views import detailed, minimalistic

router = Router(
    'model-simple/',
    [
        path(
            'user-minimalistic/',
            minimalistic.UserController.as_view(),
            name='user_minimalistic',
        ),
        path(
            'user-detailed/',
            detailed.UserController.as_view(),
            name='user_detailed',
        ),
    ],
)
