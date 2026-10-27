from http import HTTPStatus
from typing import Final

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import condition

from dmr import Controller, HeaderSpec, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.plugins.pydantic import PydanticFastSerializer

# Imitate the version of the catalog in the DB:
_CATALOG_REVISION: Final = 42


def _catalog_etag(request: HttpRequest, **kwargs: object) -> str:
    return f'"catalog-{_CATALOG_REVISION}"'


@wrap_middleware(
    condition(etag_func=_catalog_etag),
    ResponseSpec(
        return_type=None,
        status_code=HTTPStatus.NOT_MODIFIED,
        headers={'ETag': HeaderSpec()},
    ),
)
def catalog_etag_json(response: HttpResponse) -> HttpResponse:
    """Django's ``304`` response has no ``Content-Type``, set it."""
    response['Content-Type'] = 'application/json'
    return response


@catalog_etag_json
class CatalogController(Controller[PydanticFastSerializer]):
    """Returns ``304`` when the client already has the latest catalog."""

    responses = catalog_etag_json.responses

    def get(self) -> list[str]:
        return ['book', 'pen']


# run: {"controller": "CatalogController", "method": "get", "url": "/api/catalog/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "CatalogController", "method": "get", "url": "/api/catalog/", "headers": {"If-None-Match": "\"catalog-42\""}, "curl_args": ["-D", "-"], "assert-error-text": "304", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "CatalogController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
