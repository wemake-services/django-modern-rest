from collections.abc import Mapping
from http import HTTPStatus
from typing import Annotated, Any

from django.http import HttpResponse
from typing_extensions import override

from dmr import Body, Controller, HeaderSpec, NewCookie
from dmr.errors import ErrorModel
from dmr.metadata import ResponseSpecMetadata
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer


class ApiController(Controller[PydanticSerializer]):
    error_model = Annotated[
        ErrorModel,
        ResponseSpecMetadata(headers={'X-Error-Id': HeaderSpec()}),
    ]

    def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
        return parsed_body

    @override
    def to_error(
        self,
        raw_data: Any,
        *,
        status_code: HTTPStatus,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> HttpResponse:
        headers = dict(headers or {})
        headers.setdefault('X-Error-Id', 'Error-Id from your provider')

        return super().to_error(
            raw_data,
            status_code=status_code,
            headers=headers,
            cookies=cookies,
            renderer=renderer,
        )


# run: {"controller": "ApiController", "method": "post", "body": {"key": "value"}, "url": "/api/example/"}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "method": "post", "body": [], "url": "/api/example/", "assert-error-text": "from your provider", "fail-with-body": false, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
