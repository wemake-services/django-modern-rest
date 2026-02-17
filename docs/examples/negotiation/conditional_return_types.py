from typing import Annotated

import pydantic

from dmr import Body, Controller
from dmr.negotiation import ContentType, conditional_type
from dmr.plugins.msgspec import (
    MsgspecJsonParser,
    MsgspecJsonRenderer,
)
from dmr.plugins.pydantic import PydanticSerializer
from examples.negotiation.negotiation import XmlParser, XmlRenderer


class _RequestModel(pydantic.BaseModel):
    root: dict[str, str]


class ExampleController(
    Controller[PydanticSerializer],
    Body[_RequestModel],
):
    parsers = (MsgspecJsonParser(), XmlParser())
    renderers = (MsgspecJsonRenderer(), XmlRenderer())

    def post(
        self,
    ) -> Annotated[
        dict[str, str] | list[str],
        conditional_type({
            ContentType.json: list[str],
            ContentType.xml: dict[str, str],
        }),
    ]:
        if self.request.accepts(ContentType.json):
            return list(self.parsed_body.root.values())
        return self.parsed_body.root


# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Content-Type": "application/xml", "Accept": "application/xml"}, "body": {"root": {"one": "first"}}}  # noqa: E501, ERA001
# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Content-Type": "application/json", "Accept": "application/json"}, "body": {"root": {"one": "first"}}}  # noqa: E501, ERA001
