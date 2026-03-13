from dmr import Blueprint, Controller
from dmr.plugins.pydantic import PydanticSerializer


class MyBlueprint(Blueprint[PydanticSerializer]):
    semantic_responses = False

    def get(self) -> str:
        return 'will not have semantic responses'


class APIController(Controller[PydanticSerializer]):
    blueprints = (MyBlueprint,)

    def post(self) -> str:
        return 'will have semantic responses'


# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
