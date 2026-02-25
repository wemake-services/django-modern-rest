from django.urls import path

from dmr.routing import Router
from server.apps.middlewares import views

router = Router(
    [
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
        path(
            'request-id',
            views.RequestIdController.as_view(),
            name='request_id',
        ),
        path(
            'login-required',
            views.LoginRequiredController.as_view(),
            name='login_required',
        ),
        path(
            'csrf-token',
            views.CsrfTokenController.as_view(),
            name='csrf_token',
        ),
    ],
    prefix='middlewares/',
)
