from typing import Annotated, TypeAlias

import pydantic

from dmr import Body, Controller
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi.objects import MediaTypeMetadata
from dmr.plugins.msgspec import MsgspecJsonParser
from dmr.plugins.pydantic import PydanticSerializer
from examples.negotiation.negotiation import XmlParser


class _SearchModel(pydantic.BaseModel):
    search: str
    max_items: int


class XmlSearchModel(pydantic.BaseModel):
    search: str


SearchModel: TypeAlias = Annotated[
    _SearchModel,
    MediaTypeMetadata(
        example=_SearchModel(search='example', max_items=10).model_dump(
            mode='json',
        ),
    ),
]


class UserController(
    Controller[PydanticSerializer],
):
    parsers = (MsgspecJsonParser(), XmlParser())

    def post(
        self,
        parsed_body: Body[
            Annotated[
                _SearchModel | XmlSearchModel,
                conditional_type({
                    ContentType.json: SearchModel,
                    ContentType.xml: XmlSearchModel,
                }),
            ],
        ],
    ) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
