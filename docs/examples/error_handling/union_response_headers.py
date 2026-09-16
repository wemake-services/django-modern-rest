from collections.abc import Mapping
from http import HTTPStatus
from typing import Annotated, Any

import pydantic
from django.http import HttpResponse
from typing_extensions import override

from dmr import Body, Controller, HeaderSpec, NewCookie
from dmr.metadata import ResponseSpecMetadata
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer


class User(pydantic.BaseModel):
    username: str


class ApiController(Controller[PydanticSerializer]):
    def post(
        self,
        parsed_body: Body[dict[str, str]],
    ) -> (
        Annotated[
            User,
            ResponseSpecMetadata(headers={'X-User-Id': HeaderSpec()}),
        ]
        | str
    ):
        username = parsed_body.get('username')
        if username is None:
            return 'anonymous'
        return User(username=username)

    @override
    def to_response(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus | None = None,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        headers = dict(headers or {})
        if isinstance(raw_data, User):
            # Only `User` responses declare this header, so we only set it
            # here. A `str` response is documented without it.
            headers.setdefault('X-User-Id', 'User-Id from your database')

        return super().to_response(
            raw_data,
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            renderer=renderer,
        )


# run: {"controller": "ApiController", "method": "post", "body": {"username": "sobolevn"}, "url": "/api/example/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "method": "post", "body": {}, "url": "/api/example/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
