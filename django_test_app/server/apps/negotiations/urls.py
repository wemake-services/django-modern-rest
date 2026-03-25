from dmr.routing import Router, path
from server.apps.negotiations import views

router = Router(
    'negotiations/',
    [
        path(
            'negotiation/',
            views.ContentNegotiationController.as_view(),
            name='negotiation',
        ),
    ],
)
