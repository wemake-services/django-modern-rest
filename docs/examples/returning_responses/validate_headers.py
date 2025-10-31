import uuid
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from django_modern_rest import (
    Body,
    Controller,
    HeaderSpec,
    ResponseSpec,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


@final
class UserController(
    Controller[PydanticSerializer],
    Body[UserModel],
):
    @validate(
        ResponseSpec(
            UserModel,
            status_code=HTTPStatus.OK,
            headers={
                'X-Created': HeaderSpec(),
                'X-Our-Domain': HeaderSpec(required=False),
            },
        ),
    )
    def post(self) -> HttpResponse:
        uid = uuid.uuid4()
        # This response would have an explicit status code `200`
        # and one required header `X-Created` and one optional `X-Our-Domain`:
        headers = {'X-Created': str(uid)}
        if '@ourdomain.com' in self.parsed_body.email:
            headers['X-Our-Domain'] = 'true'
        return self.to_response(
            self.parsed_body,
            status_code=HTTPStatus.OK,
            headers=headers,
        )
