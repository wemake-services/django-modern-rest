import uuid
from http import HTTPStatus

import msgspec
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.openapi.objects import Link
from dmr.plugins.msgspec import MsgspecSerializer


class UserModel(msgspec.Struct):
    uid: uuid.UUID


class UserController(Controller[MsgspecSerializer]):
    @modify(
        response_description='This is a description for your response',
        links={
            'GetUser': Link(
                operation_id='getUser',
                parameters={'userId': '$response.body#/uid'},
            ),
        },
    )
    def post(self) -> UserModel:
        return UserModel(uid=uuid.uuid4())

    @validate(
        ResponseSpec(
            status_code=HTTPStatus.OK,
            return_type=UserModel,
            links={
                'GetUser': Link(
                    operation_id='getUser',
                    parameters={'userId': '$response.body#/uid'},
                ),
            },
        ),
    )
    def put(self) -> HttpResponse:
        return self.to_response(UserModel(uid=uuid.uuid4()))


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
