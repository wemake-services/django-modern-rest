from http import HTTPStatus
from typing import final

from typing_extensions import TypedDict, override

from django_modern_rest import APIError, Body, Controller, ResponseSpec, modify
from django_modern_rest.errors import ErrorType
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _ErrorDetail(TypedDict):
    msg: str


@final
class ErrorModel(TypedDict):
    detail: list[_ErrorDetail]


@final
class CustomPydanticSerializer(PydanticSerializer):
    error_model = ErrorModel

    @override
    @classmethod
    def error_serialize(
        cls,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: str | ErrorType | None = None,
    ) -> ErrorModel:
        response = super().error_serialize(
            error,
            loc=loc,
            error_type=error_type,
        )
        return {
            'detail': [{'msg': detail['msg']} for detail in response['detail']],
        }


@final
class ApiController(
    Controller[CustomPydanticSerializer],
    Body[dict[str, str]],
):
    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=CustomPydanticSerializer.error_model,
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
        ],
    )
    def post(self) -> str:
        raise APIError(
            self.serializer.error_serialize('Nope!'),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


# run: {"controller": "ApiController", "method": "post", "body": {}, "url": "/api/example/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "ApiController", "method": "post", "body": [], "url": "/api/example/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
