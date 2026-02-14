import uuid
from http import HTTPStatus

import pydantic
from django.http import HttpResponse

from django_modern_rest import (
    Body,
    Controller,
    CookieSpec,
    NewCookie,
    ResponseSpec,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class UserModel(pydantic.BaseModel):
    email: str


class UserController(
    Controller[PydanticSerializer],
    Body[UserModel],
):
    @validate(
        ResponseSpec(
            UserModel,
            status_code=HTTPStatus.CREATED,
            cookies={
                'user_id': CookieSpec(),
                'session': CookieSpec(max_age=1000, required=False),
            },
        ),
    )
    def post(self) -> HttpResponse:
        uid = uuid.uuid4()
        # This response would have one required cookie `user_id`
        # and one optional cookie `session`:
        cookies = {'user_id': NewCookie(value=str(uid))}
        if '@ourdomain.com' in self.parsed_body.email:
            cookies['session'] = NewCookie(value='true', max_age=1000)
        return self.to_response(
            self.parsed_body,
            cookies=cookies,
        )


# run: {"controller": "UserController", "method": "post", "body": {"email": "user@ourdomain.com"}, "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
