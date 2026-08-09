import json

from dmr.openapi import load_schema
from dmr.openapi.objects import PathItem
from dmr.routing import Router, external_path
from server.apps.external_views.views import (
    EXTERNAL_CLASS_OPENAPI,
    EXTERNAL_FUNC_OPENAPI,
    ExternalClass,
    external_function,
)

router = Router(
    'external_views/',
    urls=[
        external_path(
            'external_function/',
            external_function,
            name='external_function',
            openapi=load_schema(json.loads(EXTERNAL_FUNC_OPENAPI), PathItem),
        ),
        external_path(
            'external_class/',
            ExternalClass.as_view(),
            name='external_class',
            openapi=load_schema(json.loads(EXTERNAL_CLASS_OPENAPI), PathItem),
        ),
    ],
)
