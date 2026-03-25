from collections.abc import AsyncIterator
from typing import Literal, TypeAlias

import pydantic
from django.http import HttpRequest
from pydantic.json_schema import SkipJsonSchema

from dmr.plugins.pydantic import PydanticSerializer
from dmr.sse import SSEContext, SSEResponse, sse


class _BaseEvent(pydantic.BaseModel):
    comment: SkipJsonSchema[str | None] = None
    retry: SkipJsonSchema[int | None] = None

    @property
    def should_serialize_data(self) -> bool:
        return True


class UserEvent(_BaseEvent):
    event: Literal['user'] = 'user'
    id: int
    data: str  # username


class _Payment(pydantic.BaseModel):
    amount: int
    currency: str


class PaymentEvent(_BaseEvent):
    id: SkipJsonSchema[None] = None
    event: Literal['payment'] = 'payment'
    data: pydantic.Json[_Payment]


class PingEvent(pydantic.BaseModel):
    retry: int = 100
    comment: Literal['ping'] = 'ping'
    id: SkipJsonSchema[None] = None
    data: SkipJsonSchema[None] = None
    event: SkipJsonSchema[None] = None

    @property
    def should_serialize_data(self) -> bool:
        return False


_PossibleEvents: TypeAlias = UserEvent | PaymentEvent | PingEvent


async def complex_events() -> AsyncIterator[_PossibleEvents]:
    yield UserEvent(id=1, data='sobolevn')
    yield PaymentEvent(
        data=_Payment(
            amount=10,
            currency='$',
        ).model_dump_json(),
    )
    yield PingEvent()


@sse(PydanticSerializer)
async def complex_sse(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[_PossibleEvents]:
    return SSEResponse(complex_events())


# run: {"controller": "complex_sse", "method": "get"}  # noqa: ERA001
