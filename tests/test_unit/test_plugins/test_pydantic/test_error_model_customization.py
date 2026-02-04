import json
from http import HTTPStatus
from typing import final

from dirty_equals import IsStr
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict, override

from django_modern_rest import APIError, Body, Controller, ResponseSpec, modify
from django_modern_rest.errors import ErrorType
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _ErrorDetail(TypedDict):
    msg: str


@final
class _ErrorModel(TypedDict):
    detail: list[_ErrorDetail]


@final
class _CustomPydanticSerializer(PydanticSerializer):
    error_model = _ErrorModel

    @override
    @classmethod
    def error_serialize(
        cls,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: str | ErrorType | None = None,
    ) -> _ErrorModel:
        response = super().error_serialize(
            error,
            loc=loc,
            error_type=error_type,
        )
        return {
            'detail': [{'msg': detail['msg']} for detail in response['detail']],
        }


@final
class _CustomErrorModelController(
    Controller[_CustomPydanticSerializer],
    Body[dict[str, str]],
):
    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=_CustomPydanticSerializer.error_model,
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
        ],
    )
    def post(self) -> str:
        raise APIError(
            self.serializer.error_serialize('test msg'),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


def test_error_message_serializer_customization(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can customize error message via serializer."""
    metadata = _CustomErrorModelController.api_endpoints['POST'].metadata
    assert metadata.responses == snapshot({
        HTTPStatus.PAYMENT_REQUIRED: ResponseSpec(
            return_type=_ErrorModel,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        ),
        HTTPStatus.CREATED: ResponseSpec(
            return_type=str,
            status_code=HTTPStatus.CREATED,
        ),
        HTTPStatus.BAD_REQUEST: ResponseSpec(
            return_type=_ErrorModel,
            status_code=HTTPStatus.BAD_REQUEST,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=_ErrorModel,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })

    request = dmr_rf.post('/whatever/', data={})

    response = _CustomErrorModelController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'test msg'}],
    })
