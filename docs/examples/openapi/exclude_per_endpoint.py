from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class APIController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'will have semantic responses'

    @modify(exclude_semantic_responses={HTTPStatus.UNPROCESSABLE_ENTITY})
    def post(self) -> str:
        return 'will not have semantic response with 422 status code'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
