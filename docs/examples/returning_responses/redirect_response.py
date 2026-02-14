from http import HTTPStatus
from typing import Final

from django.http import HttpResponse, HttpResponseRedirect

from django_modern_rest import (
    Controller,
    HeaderSpec,
    validate,
)
from django_modern_rest.metadata import ResponseSpec
from django_modern_rest.plugins.pydantic import PydanticSerializer

_RedirectSpec: Final = ResponseSpec(
    None,
    status_code=HTTPStatus.FOUND,
    headers={'Location': HeaderSpec()},
)


class UserController(Controller[PydanticSerializer]):
    @validate(_RedirectSpec)
    def get(self) -> HttpResponse:
        return HttpResponseRedirect('https://example.com/api/new/user/list')


# run: {"controller": "UserController", "method": "get", "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
