import uuid
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from django_modern_rest import (
    Body,
    Controller,
    HeaderDescription,
    ResponseDescription,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserModel(UserCreateModel):
    uid: uuid.UUID


@final
class UserController(
    Controller[PydanticSerializer],
    Body[UserCreateModel],
):
    @validate(  # <- describes all possible return types from this endpoint
        ResponseDescription(
            UserModel,
            status_code=HTTPStatus.OK,
            headers={'X-Created': HeaderDescription()},
        ),
    )
    def post(self) -> HttpResponse:
        uid = uuid.uuid4()
        # This response would have an explicit status code `200`
        # and new explicit header `{'X-Created': obj_uuid}`:
        return self.to_response(
            UserModel(uid=uid, email=self.parsed_body.email),
            status_code=HTTPStatus.OK,
            headers={'X-Created': str(uid)},
        )
