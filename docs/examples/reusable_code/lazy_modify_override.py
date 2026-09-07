from http import HTTPStatus
from typing import ClassVar

from typing_extensions import override

from dmr import modify
from dmr.endpoint import ModifyAnyCallable
from dmr.plugins.pydantic import PydanticFastSerializer
from examples.reusable_code.lazy_modify import LoginController


class OurLoginController(LoginController[PydanticFastSerializer]):
    status_code: ClassVar[HTTPStatus] = HTTPStatus.IM_USED

    @classmethod
    @override
    def lazy_spec(cls) -> ModifyAnyCallable:
        return modify(status_code=cls.status_code, tags=['custom_openapi_meta'])


# run: {"controller": "OurLoginController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "OurLoginController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
