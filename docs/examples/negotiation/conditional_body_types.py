from typing import Annotated

import pydantic

from dmr import Body, Controller
from dmr.negotiation import ContentType, conditional_type
from dmr.plugins.msgspec import MsgspecJsonParser, MsgspecJsonRenderer
from dmr.plugins.pydantic import PydanticSerializer
from examples.negotiation.negotiation import XmlParser, XmlRenderer


class _XMLRequestModel(pydantic.BaseModel):
    root: dict[str, str]


class ExampleController(
    Controller[PydanticSerializer],
    Body[
        Annotated[
            # The body will be a union of these two types:
            _XMLRequestModel | dict[str, str],
            conditional_type({
                # But, for json it will always be:
                ContentType.json: dict[str, str],
                # And for xml it will always be:
                ContentType.xml: _XMLRequestModel,
            }),
        ],
    ],
):
    parsers = (MsgspecJsonParser(), XmlParser())
    renderers = (MsgspecJsonRenderer(), XmlRenderer())

    def post(self) -> dict[str, str]:
        if isinstance(self.parsed_body, _XMLRequestModel):
            return self.parsed_body.root
        return self.parsed_body


# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Content-Type": "application/xml", "Accept": "application/xml"}, "body": {"root": {"one": "first"}}}  # noqa: E501, ERA001
# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Content-Type": "application/json", "Accept": "application/json"}, "body": {"one": "first"}}  # noqa: E501, ERA001
# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Content-Type": "application/json", "Accept": "application/json"}, "body": {"root": {"mixin-json-content-type": "with-xml-format"}}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: E501, ERA001
