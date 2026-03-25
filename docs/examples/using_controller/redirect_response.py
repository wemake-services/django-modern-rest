from http import HTTPStatus

from django.http import HttpResponse, HttpResponseRedirect

from dmr import Controller, HeaderSpec, validate
from dmr.metadata import ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer


class UserController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            None,
            status_code=HTTPStatus.FOUND,
            headers={'Location': HeaderSpec()},
        ),
    )
    def get(self) -> HttpResponse:
        return HttpResponseRedirect(
            'https://example.com/api/new/user/list',
            content_type='application/json',
        )


# run: {"controller": "UserController", "method": "get", "url": "/api/user/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
