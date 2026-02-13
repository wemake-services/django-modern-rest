import json
from http import HTTPStatus
from typing import final

from dirty_equals import IsStr
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import (
    APIError,
    Blueprint,
    Body,
    Controller,
    ResponseSpec,
    modify,
)
from django_modern_rest.errors import ErrorType, format_error
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.django_session import DjangoSessionSyncAuth
from django_modern_rest.test import DMRRequestFactory


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
        loc: str | None = None,
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
    Body[dict[str, str]],
):
    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=_CustomErrorModel,
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            ),
        ],
    )
    def post(self) -> str:
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


@final
class _CustomMessageBlueprint(
    _CustomErrorMixin,
    Blueprint[PydanticSerializer],
    Body[dict[str, str]],
):
    responses = (
        ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        ),
    )

    def post(self) -> str:
        raise APIError(
            self.format_error('test msg'),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
        )


@final
class _BlueprintController(_CustomErrorMixin, Controller[PydanticSerializer]):
    blueprints = (_CustomMessageBlueprint,)
    auth = (DjangoSessionSyncAuth(),)


def test_error_message_blueprint_customization(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can customize error message via blueprint."""
    metadata = _BlueprintController.api_endpoints['POST'].metadata
    assert metadata.responses == snapshot({
        HTTPStatus.CREATED: ResponseSpec(
            return_type=str,
            status_code=HTTPStatus.CREATED,
        ),
        # From blueprint:
        HTTPStatus.PAYMENT_REQUIRED: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.PAYMENT_REQUIRED,
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
        # From controller:
        HTTPStatus.UNAUTHORIZED: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.UNPROCESSABLE_ENTITY: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.FORBIDDEN: ResponseSpec(
            return_type=_CustomErrorModel,
            status_code=HTTPStatus.FORBIDDEN,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })

    request = dmr_rf.post('/whatever/', data={})
    _fill_csrf(request)
    request.user = User()
    response = _BlueprintController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert json.loads(response.content) == snapshot({
        'error': [{'message': 'test msg'}],
    })

    request = dmr_rf.post('/whatever/', data=[])
    _fill_csrf(request)
    request.user = User()
    response = _BlueprintController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'error': [{'message': 'Input should be a valid dictionary'}],
    })

    request = dmr_rf.post('/whatever/', data=[])
    request.user = User()
    response = _BlueprintController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN, response.content
    assert json.loads(response.content) == snapshot({
        'error': [{'message': 'CSRF Failed: CSRF cookie not set.'}],
    })

    request = dmr_rf.post('/whatever/', data={})
    request.user = AnonymousUser()
    response = _BlueprintController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'error': [{'message': 'Not authenticated'}],
    })
