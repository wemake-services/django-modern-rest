from http import HTTPStatus

import pydantic

from dmr import APIError, Controller, Query, ResponseSpec
from dmr.negotiation import ContentType
from dmr.plugins.msgspec import MsgspecJsonParser, MsgspecJsonRenderer
from dmr.plugins.pydantic import PydanticSerializer
from examples.negotiation.negotiation import XmlParser, XmlRenderer


class _QueryModel(pydantic.BaseModel):
    show_error: bool = False


class ExampleController(Controller[PydanticSerializer], Query[_QueryModel]):
    parsers = (MsgspecJsonParser(), XmlParser())
    renderers = (MsgspecJsonRenderer(), XmlRenderer())
    responses = (
        ResponseSpec(
            list[str],
            status_code=HTTPStatus.CONFLICT,
            limit_to_content_types={ContentType.json},
        ),
        ResponseSpec(
            dict[str, str],
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            limit_to_content_types={ContentType.xml},
        ),
    )

    def get(self) -> str:
        if self.request.accepts(ContentType.json):
            if self.parsed_query.show_error:
                # This is explicitly wrong:
                # `PAYMENT_REQUIRED` cannot happen with `json`,
                # response validation will catch this:
                raise APIError([], status_code=HTTPStatus.PAYMENT_REQUIRED)
            raise APIError(['wrong', 'items'], status_code=HTTPStatus.CONFLICT)
        raise APIError(
            {'wrong': 'items'},
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


# run: {"controller": "ExampleController", "method": "get", "url": "/api/example/", "headers": {"Accept": "application/json"}, "fail-with-body": false}  # noqa: E501, ERA001
# run: {"controller": "ExampleController", "method": "get", "url": "/api/example/", "headers": {"Accept": "application/xml"}, "fail-with-body": false}  # noqa: E501, ERA001
# run: {"controller": "ExampleController", "method": "get", "url": "/api/example/", "headers": {"Accept": "application/json"}, "query": "?show_error=1", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: E501, ERA001
