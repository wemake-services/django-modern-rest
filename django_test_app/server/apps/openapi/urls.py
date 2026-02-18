from django.urls import URLPattern

from dmr.openapi import openapi_spec
from dmr.openapi.renderers import (
    JsonRenderer,
    RedocRenderer,
    ScalarRenderer,
    SwaggerRenderer,
)
from dmr.routing import Router
from server.apps.openapi.config import (
    get_openapi_config,
)


def build_spec(router: Router) -> tuple[list[URLPattern], str, str]:
    return openapi_spec(
        router=router,
        renderers=[
            SwaggerRenderer(),
            JsonRenderer(),
            ScalarRenderer(),
            RedocRenderer(),
        ],
        config=get_openapi_config(),
    )
