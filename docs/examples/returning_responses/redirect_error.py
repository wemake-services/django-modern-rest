from http import HTTPStatus
from typing import Final

from django.http import HttpResponse

from dmr import (
    APIRedirectError,
    Controller,
    HeaderSpec,
    modify,
    validate,
)
from dmr.metadata import ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer

_RedirectSpec: Final = ResponseSpec(
    None,
    status_code=HTTPStatus.FOUND,
    headers={'Location': HeaderSpec()},
)


class UserController(Controller[PydanticSerializer]):
    @validate(_RedirectSpec)
    def get(self) -> HttpResponse:
        raise APIRedirectError('https://example.com/api/new/user/list')

    @modify(extra_responses=[_RedirectSpec])
    def post(self) -> dict[str, str]:
        raise APIRedirectError('https://example.com/api/new/user/create')


# run: {"controller": "UserController", "method": "get", "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "post", "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
