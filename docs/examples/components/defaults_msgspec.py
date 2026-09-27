import msgspec

from dmr import Body, Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer


class ProductFilters(msgspec.Struct):
    category: str


# Defaults are passed as-is, so structs used as defaults must be frozen:
class Pagination(msgspec.Struct, frozen=True):
    page: int = 1


DEFAULT_PAGINATION = Pagination()


class ProductController(Controller[MsgspecSerializer]):
    def post(
        self,
        # Correct: `None` is inside the component annotation
        parsed_body: Body[ProductFilters | None] = None,
        # Defaults can be of the same type as the model:
        parsed_query: Query[Pagination] = DEFAULT_PAGINATION,
    ) -> dict[str, str | int]:
        return {
            'category': 'all' if parsed_body is None else parsed_body.category,
            'page': parsed_query.page,
        }


# run: {"controller": "ProductController", "url": "/api/products/", "method": "post"}  # noqa: ERA001, E501
# run: {"controller": "ProductController", "url": "/api/products/", "method": "post", "query": "?page=2", "body": {"category": "cars"}}  # noqa: ERA001, E501
# openapi: {"controller": "ProductController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
