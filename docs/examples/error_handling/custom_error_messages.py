from http import HTTPStatus

from typing_extensions import TypedDict, override

from dmr import APIError, Body, Controller, ResponseSpec, modify
from dmr.errors import ErrorType, format_error
from dmr.plugins.pydantic import PydanticSerializer


class CustomErrorDetail(TypedDict):
    message: str


class CustomErrorModel(TypedDict):
    errors: list[CustomErrorDetail]


class ApiController(Controller[PydanticSerializer]):
    error_model = CustomErrorModel

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> CustomErrorModel:
        default = format_error(
            error,
            loc=loc,
            error_type=error_type,
        )
        return {
            'errors': [
                {'message': detail['msg']} for detail in default['detail']
            ],
        }

    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=CustomErrorModel,
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
        ],
    )
    def post(self, parsed_body: Body[dict[str, str]]) -> str:
        raise APIError(
            self.format_error('test msg'),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


# run: {"controller": "ApiController", "method": "post", "body": {}, "url": "/api/example/",  "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "method": "post", "body": [], "url": "/api/example/", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ApiController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
