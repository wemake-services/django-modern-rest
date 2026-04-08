from http import HTTPStatus

from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller, ResponseSpec
from dmr.endpoint import Endpoint
from dmr.errors import ErrorModel, ErrorType
from dmr.negotiation import ContentType
from dmr.plugins.msgspec import MsgspecJsonRenderer, MsgspecSerializer
from dmr.plugins.pydantic import PydanticSerializer
from dmr.problem_details import (
    ProblemDetailsError,
    ProblemDetailsModel,
    conditional_error,
    format_error,
)


class ProblemDetailsController(Controller[MsgspecSerializer]):
    renderers = (
        MsgspecJsonRenderer(ContentType.json),
        MsgspecJsonRenderer(ContentType.json_problem_details),
    )

    error_model = ProblemDetailsError.build_error_model({
        ContentType.json: ErrorModel,
    })

    responses = (
        ResponseSpec(error_model, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )

    async def get(self) -> None:
        raise conditional_error(
            self.request,
            detail='Your current balance is 10, but the price is 15',
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            type='https://example.com/probs/out-of-credit',
            title='Not enough funds',
            instance='/account/users/1/',
            extra={'balance': 10, 'price': 15},
        )

    @override
    async def handle_async_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ProblemDetailsError):
            return exc.to_error(controller)
        return await super().handle_async_error(
            endpoint,
            controller,
            exc,
        )

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> ErrorModel | ProblemDetailsModel:
        return format_error(error, loc=loc, error_type=error_type)
