import json
from http import HTTPStatus
from typing import final

from dirty_equals import IsStr
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from dmr import (
    APIError,
    Body,
    Controller,
    ResponseSpec,
    modify,
)
from dmr.errors import ErrorType, format_error
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


def _fill_csrf(request: HttpRequest) -> HttpRequest:
    csrf_token = get_token(request)
    request.META['HTTP_X_CSRFTOKEN'] = csrf_token
    request.COOKIES['csrftoken'] = csrf_token
    return request


@final
class _ErrorDetail(TypedDict):
    message: str


@final
class _CustomErrorModel(TypedDict):
    error: list[_ErrorDetail]


class _CustomErrorMixin:
    error_model = _CustomErrorModel

    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> _CustomErrorModel:
        default = format_error(
            error,
            loc=loc,
            error_type=error_type,
        )
        return {
            'error': [
                {'message': detail['msg']} for detail in default['detail']
            ],
        }


@final
class _CustomErrorModelController(
    _CustomErrorMixin,
    Controller[PydanticSerializer],
):
    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=_CustomErrorModel,
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
        ],
    )
    def post(self, parsed_body: Body[dict[str, str]]) -> str:
        raise APIError(
            self.format_error('test msg'),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


def test_error_message_controller_customization(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can customize error message via controller."""
    metadata = _CustomErrorModelController.api_endpoints['POST'].metadata
    assert metadata.responses == snapshot({
        HTTPStatus.PAYMENT_REQUIRED: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        ),
        HTTPStatus.CREATED: ResponseSpec(
            return_type=str,
            status_code=HTTPStatus.CREATED,
        ),
        HTTPStatus.BAD_REQUEST: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.BAD_REQUEST,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.UNPROCESSABLE_ENTITY: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })

    request = dmr_rf.post('/whatever/', data={})

    response = _CustomErrorModelController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == snapshot({
        'error': [{'message': 'test msg'}],
    })
