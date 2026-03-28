from collections.abc import AsyncIterator
from typing import Literal, TypeAlias

import pydantic
from pydantic.json_schema import SkipJsonSchema

from dmr.errors import ErrorModel
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming.sse import SSEController


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


class ErrorEvent(_BaseEvent):
    # Can happen if event validation will fail:
    id: SkipJsonSchema[None] = None
    event: Literal['error'] = 'error'
    data: pydantic.Json[ErrorModel]


_PossibleEvents: TypeAlias = UserEvent | PaymentEvent | PingEvent | ErrorEvent


class ComplexEventsController(SSEController[PydanticSerializer]):
    def get(self) -> AsyncIterator[_PossibleEvents]:
        return self.complex_events()

    async def complex_events(self) -> AsyncIterator[_PossibleEvents]:
        yield UserEvent(id=1, data='sobolevn')
        yield PaymentEvent(
            data=_Payment(
                amount=10,
                currency='$',
            ).model_dump_json(),
        )
        yield PingEvent()


# run: {"controller": "ComplexEventsController", "method": "get"}  # noqa: ERA001, E501
# openapi: {"controller": "ComplexEventsController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
