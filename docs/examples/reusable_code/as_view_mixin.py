import logging
from typing import Any, Final

from django.http import HttpRequest, HttpResponseBase
from django.views import View
from typing_extensions import override

from dmr import Controller
from dmr.openapi import build_schema
from dmr.openapi.views import OpenAPIJsonView
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import Router, path

_LOGGER: Final = logging.getLogger(__name__)


class LoggingMixin(View):
    """Logs the status code of every response."""

    log_format: str = '{method} {path}: {status_code}'

    @override
    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        response = super().dispatch(request, *args, **kwargs)
        _LOGGER.info(
            self.log_format.format(
                method=request.method,
                path=request.path,
                status_code=response.status_code,
            ),
        )
        return response


class CatalogController(LoggingMixin, Controller[PydanticFastSerializer]):
    def get(self) -> list[str]:
        return ['book', 'pen']


router = Router(
    'api/',
    [
        path(
            'catalog/',
            CatalogController.as_view(log_format='Catalog: {status_code}'),
            name='catalog',
        ),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
    path(
        'docs/openapi.json/',
        OpenAPIJsonView.as_view(build_schema(router)),
        name='openapi_json',
    ),
]

# run: {"method": "get", "url": "/api/catalog/", "use_urlpatterns": true}  # noqa: ERA001
# openapi: {"openapi_url": "/docs/openapi.json/", "use_urlpatterns": true}  # noqa: ERA001
