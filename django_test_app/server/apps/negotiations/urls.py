from django.urls import path

from dmr.routing import Router
from server.apps.negotiations import views

router = Router(
    [
        path(
            'negotiation',
            views.ContentNegotiationController.as_view(),
            name='negotiation',
        ),
    ],
    prefix='negotiations/',
)
