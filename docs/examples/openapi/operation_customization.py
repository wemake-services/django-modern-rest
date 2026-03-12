from http import HTTPStatus

from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi.objects import Server
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    @modify(servers=[Server(url='https://example.com')])
    def post(self) -> str:
        return 'post'

    @validate(
        ResponseSpec(status_code=HTTPStatus.OK, return_type=str),
        description='PUT operation description',
        tags=['Public'],
    )
    def put(self) -> HttpResponse:
        return self.to_response('put')
