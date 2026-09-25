from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class MyBaseController(Controller[PydanticSerializer]):
    # It has an exact serializer and an endpoint,
    # but we only want to reuse it, we don't want to route it:
    is_abstract = True

    def get(self) -> str:
        return 'hello from the base controller'


class MyController(MyBaseController):
    """It does not declare `is_abstract`, so it is concrete again."""

    # It serves the same `GET` request as `MyBaseController`,
    # but this one builds its endpoints and can be routed.


# run: {"controller": "MyController", "method": "get", "url": "/api/example/"}  # noqa: ERA001
# openapi: {"controller": "MyController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
