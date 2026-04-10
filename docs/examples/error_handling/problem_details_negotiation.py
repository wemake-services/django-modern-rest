from http import HTTPStatus
from typing import Any

from typing_extensions import override

from dmr import Controller, ResponseSpec
from dmr.errors import ErrorModel, ErrorType
from dmr.negotiation import ContentType, accepts
from dmr.plugins.pydantic import PydanticSerializer
from dmr.problem_details import ProblemDetailsError
from dmr.renderers import JsonRenderer


class ProblemDetailsController(Controller[PydanticSerializer]):
    error_model = ProblemDetailsError.error_model({
        ContentType.json: ErrorModel,
    })

    renderers = (
        JsonRenderer(ContentType.json),
        JsonRenderer(ContentType.json_problem_details),
    )

    responses = (
        ResponseSpec(error_model, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )

    async def get(self) -> str:
        raise ProblemDetailsError.conditional_error(
            'Your current balance is 0, but the price is 15',
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            type='https://example.com/probs/out-of-credit',
            title='Not enough funds',
            instance='/account/users/1/',
            extra={'balance': 0, 'price': 15},
            controller=self,
        )

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:
        if accepts(self.request, ContentType.json_problem_details):
            return ProblemDetailsError.format_error(
                error,
                loc=loc,
                error_type=error_type,
                title='From format_error',
            )
        return super().format_error(error, loc=loc, error_type=error_type)


# run: {"controller": "ProblemDetailsController", "method": "get", "url": "/api/balance/", "assert-error-text": "current balance", "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "ProblemDetailsController", "method": "get", "headers": {"Accept": "application/problem+json"}, "url": "/api/balance/", "assert-error-text": "current balance",  "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ProblemDetailsController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001, E501
