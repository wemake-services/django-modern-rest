from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.errors import ErrorModel
from dmr.negotiation import ContentType
from dmr.plugins.msgspec import MsgspecJsonRenderer, MsgspecSerializer
from dmr.plugins.pydantic import PydanticSerializer
from dmr.problem_details import ProblemDetailsError


class ProblemDetailsController(Controller[MsgspecSerializer]):
    renderers = (
        MsgspecJsonRenderer(ContentType.json),
        MsgspecJsonRenderer(ContentType.json_problem_details),
    )

    error_model = ProblemDetailsError.build_error_model({
        ContentType.json: ErrorModel,
    })

    async def get(self) -> None:
        raise ProblemDetailsError(
            type='https://example.com/probs/out-of-credit',
            title='Your balance is not enough.',
            detail='Your current balance is 10, but the price is 15.',
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
        # Will handle errors in all endpoints.
        if isinstance(exc, ProblemDetailsError):
            return exc.to_error(controller)
        # Handle errors from super:
        return await super().handle_async_error(
            endpoint,
            controller,
            exc,
        )
