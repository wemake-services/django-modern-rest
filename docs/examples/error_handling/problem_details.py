from http import HTTPStatus
from typing import Any

import pydantic
from typing_extensions import override

from dmr import Controller, Query, ResponseSpec
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.problem_details import ProblemDetailsError, ProblemDetailsModel


class _QueryModel(pydantic.BaseModel):
    number: int = 0


class ProblemDetailsController(Controller[PydanticSerializer]):
    error_model = ProblemDetailsModel

    responses = (
        ResponseSpec(error_model, status_code=HTTPStatus.PAYMENT_REQUIRED),
    )

    async def get(self, parsed_query: Query[_QueryModel]) -> str:
        raise ProblemDetailsError(
            (
                f'Your current balance is {parsed_query.number}, '
                'but the price is 15'
            ),
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            type='https://example.com/probs/out-of-credit',
            title='Not enough funds',
            instance='/account/users/1/',
            extra={'balance': parsed_query.number, 'price': 15},
        )

    @override
    def format_error(
        self,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
    ) -> Any:
        return ProblemDetailsError.format_error(
            error,
            loc=loc,
            error_type=error_type,
            title='From format_error',
        )


# run: {"controller": "ProblemDetailsController", "method": "get", "url": "/api/balance/", "assert-error-text": "current balance", "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "ProblemDetailsController", "method": "get", "url": "/api/balance/", "query": "?number=a", "assert-error-text": "unable to parse string", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ProblemDetailsController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001, E501
