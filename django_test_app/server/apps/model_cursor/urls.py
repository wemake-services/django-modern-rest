from dmr.routing import Router, path
from server.apps.model_cursor import async_views, views

router = Router(
    'model-cursor/',
    [
        path(
            'entries/',
            views.EntryController.as_view(),
            name='entries',
        ),
        path(
            'entries-async/',
            async_views.EntryAsyncController.as_view(),
            name='entries_async',
        ),
    ],
    tags=['model_cursor'],
)
