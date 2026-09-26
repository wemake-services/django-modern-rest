from typing import Annotated

import pydantic

from dmr import Body, Controller
from dmr.openapi.objects import MediaTypeMetadata
from dmr.plugins.pydantic import PydanticFastSerializer


class SearchModel(pydantic.BaseModel):
    search: str
    max_items: int


example = SearchModel(search='example', max_items=10).model_dump(mode='json')


class UserController(Controller[PydanticFastSerializer]):
    def post(
        self,
        parsed_body: Body[
            Annotated[
                SearchModel,
                MediaTypeMetadata(
                    example=example,
                ),
            ]
        ],
    ) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
