from django.urls import path

from django_modern_rest.routing import Router
from server.apps.negotiations import views

router = Router([
    path(
        'negotiation',
        views.ContentNegotiationController.as_view(),
        name='negotiation',
    ),
])
