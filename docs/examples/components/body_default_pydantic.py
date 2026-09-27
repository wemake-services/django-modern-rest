import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer


class ProductFilters(pydantic.BaseModel):
    category: str


class ProductController(Controller[PydanticSerializer]):
    def post(
        self,
        parsed_body: Body[ProductFilters | None] = None,
    ) -> str:
        return 'all' if parsed_body is None else parsed_body.category


# run: {"controller": "ProductController", "url": "/api/products/", "method": "post"}  # noqa: ERA001, E501
# run: {"controller": "ProductController", "url": "/api/products/", "method": "post", "body": {"category": "cars"}}  # noqa: ERA001, E501
# run: {"controller": "ProductController", "url": "/api/products/", "method": "post", "body": {"other": "cars"}, "curl_args": ["-D", "-"], "assert-error-text": "category", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ProductController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
