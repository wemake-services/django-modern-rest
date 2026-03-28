import dataclasses
from collections.abc import AsyncIterator

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security.django_session import DjangoSessionAsyncAuth
from dmr.streaming.sse import SSEController, SSEvent


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


class UserEventsController(SSEController[MsgspecSerializer]):
    auth = (DjangoSessionAsyncAuth(),)

    async def get(self) -> AsyncIterator[SSEvent[_User]]:
        return self.produce_user_events()

    async def produce_user_events(self) -> AsyncIterator[SSEvent[_User]]:
        # You can send complex data, including json.
        # All SSEvent fields can be customized:
        yield SSEvent(
            _User(email='first@example.com'),
            event='user',
        )


# run: {"controller": "UserEventsController", "method": "get", "url": "/api/user/events/", "fail-with-body": false, "assert-error-text": "Not authenticated"}  # noqa: ERA001, E501
