from http import HTTPStatus
from typing import ClassVar

from dmr.plugins.pydantic import PydanticFastSerializer
from examples.reusable_code.lazy_validate import LoginController


class OurLoginController(LoginController[PydanticFastSerializer]):
    status_code: ClassVar[HTTPStatus] = HTTPStatus.IM_USED


# run: {"controller": "OurLoginController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "OurLoginController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
