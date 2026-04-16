from http import HTTPStatus
from typing import TypedDict

from django.http import JsonResponse

from dmr import Body, Controller, ResponseSpec, validate
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.settings import default_parser, default_renderer
from examples.negotiation.negotiation import XmlParser, XmlRenderer


class _UserInputData(TypedDict):
    email: str


class UserController(Controller[MsgspecSerializer]):
    parsers = (XmlParser(), default_parser)
    renderers = (XmlRenderer(), default_renderer)
    validate_negotiation = False

    @validate(ResponseSpec(_UserInputData, status_code=HTTPStatus.OK))
    def post(self, parsed_body: Body[_UserInputData]) -> JsonResponse:
        # NOTE: do not do this!
        return JsonResponse(parsed_body)


# run: {"controller": "UserController", "method": "post", "url": "/api/user/", "headers": {"Content-Type": "application/xml", "Accept": "application/xml"}, "body": {"email": "user@example.com"}}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json", "skip_validation": true}  # noqa: ERA001, E501
