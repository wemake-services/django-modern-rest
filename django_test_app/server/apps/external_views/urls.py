import json

from dmr.openapi import load_schema
from dmr.openapi.objects import PathItem
from dmr.routing import Router, path
from server.apps.external_views.views import (
    EXTERNAL_CLASS_OPENAPI,
    EXTERNAL_FUNCTION_OPENAPI,
    ExternalClass,
    external_function,
)

router = Router(
    'external_views/',
    [],
    external_urls=[
        (
            path(
                'external_function/',
                external_function,
                name='external_function',
            ),
            load_schema(json.loads(EXTERNAL_FUNCTION_OPENAPI), PathItem),
        ),
        (
            path(
                'external_class/',
                ExternalClass.as_view(),
                name='external_class',
            ),
            load_schema(json.loads(EXTERNAL_CLASS_OPENAPI), PathItem),
        ),
    ],
)
