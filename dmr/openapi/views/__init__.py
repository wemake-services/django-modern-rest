from contextlib import suppress

from dmr.openapi.views.base import OpenAPIView as OpenAPIView
from dmr.openapi.views.json import OpenAPIJsonView as OpenAPIJsonView
from dmr.openapi.views.redoc import RedocView as RedocView
from dmr.openapi.views.scalar import ScalarView as ScalarView
from dmr.openapi.views.stoplight import StoplightView as StoplightView
from dmr.openapi.views.swagger import SwaggerView as SwaggerView

with suppress(ImportError):
    from dmr.openapi.views.yaml import OpenAPIYamlView as OpenAPIYamlView
