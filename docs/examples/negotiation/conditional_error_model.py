from typing import Annotated, TypedDict

import pydantic
from typing_extensions import override

from dmr import Body, Controller
from dmr.errors import ErrorModel, ErrorType
from dmr.negotiation import ContentType, conditional_type
from dmr.plugins.msgspec import MsgspecJsonRenderer
from dmr.plugins.pydantic import PydanticSerializer
from examples.negotiation.negotiation import XmlRenderer


class _RequestModel(pydantic.BaseModel):
    root: dict[str, str]


class _CustomXmlErrorModel(TypedDict):
    xml_errors: dict[str, str]


class ExampleController(
    Controller[PydanticSerializer],
    Body[_RequestModel],
):
    renderers = (MsgspecJsonRenderer(), XmlRenderer())
    error_model = Annotated[
        ErrorModel | _CustomXmlErrorModel,
        conditional_type({
            ContentType.json: ErrorModel,
            ContentType.xml: _CustomXmlErrorModel,
        }),
    ]

    def post(self) -> str:
        # Will not be called in this example, because we fail to parse body:
        raise NotImplementedError

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: str | ErrorType | None = None,
    ) -> ErrorModel | _CustomXmlErrorModel:
        original: ErrorModel = super().format_error(
            error,
            loc=loc,
            error_type=error_type,
        )
        if self.request.accepts(ContentType.json):
            return original
        return {
            'xml_errors': {
                '.'.join(str(location) for location in detail['loc']): detail[
                    'msg'
                ]
                for detail in original['detail']
            },
        }


# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Accept": "application/json"}, "body": {}, "fail-with-body": false}  # noqa: E501, ERA001
# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "headers": {"Accept": "application/xml"}, "body": {}, "fail-with-body": false}  # noqa: E501, ERA001
