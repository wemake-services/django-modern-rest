import dataclasses
from collections.abc import (
    AsyncIterator,
    Mapping,
)
from typing import (
    Generic,
    NamedTuple,
    TypeAlias,
    final,
)

from typing_extensions import TypeVar

from dmr.cookies import NewCookie


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEvent:
    """
    Server sent event.

    Attributes:
        data: Event payload.
        event: Event type.
        id: Unique event's identification.
        retry: The reconnection time.
        comment: Comment about the event.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#fields

    """

    # NOTE: `str | bytes` is not supported by `msgspec`,
    # but, since it is very common to return json
    # which has `bytes` by default in our serializers - we use `bytes`.
    data: bytes | int  # noqa: WPS110
    event: str | None = dataclasses.field(default=None, kw_only=True)
    id: int | str | None = dataclasses.field(default=None, kw_only=True)
    retry: int | None = dataclasses.field(default=None, kw_only=True)
    comment: str | None = dataclasses.field(default=None, kw_only=True)


SSEData: TypeAlias = int | bytes | SSEvent
"""Types that we allow to yield from async events producer iterator."""


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEResponse:
    """
    Future response representation.

    Not a real response.
    We need this type, because creating
    :class:`dmr.sse.stream.SSEStreamingResponse` is quite complex.
    We don't want users to have a complicated API.
    So, instead: return this metadata class,
    we will transform it to the stream later on.

    Attributes:
        streaming_content: Async iterator of server sent events.
        headers: Headers to be set on the response object.
    """

    streaming_content: AsyncIterator[SSEData]
    headers: Mapping[str, str] | None = None
    cookies: Mapping[str, NewCookie] | None = None


_PathT = TypeVar('_PathT', default=None)
_QueryT = TypeVar('_QueryT', default=None)
_HeadersT = TypeVar('_HeadersT', default=None)
_CookiesT = TypeVar('_CookiesT', default=None)


@final
class SSEContext(NamedTuple, Generic[_PathT, _QueryT, _HeadersT, _CookiesT]):
    """
    Parsed context for the SSE endpoint.

    All properties always exist.
    If some component parser is not passed, we provide ``None`` as a default.
    All properties here have type vars that default to ``None`` as well.
    """

    parsed_path: _PathT
    parsed_query: _QueryT
    parsed_headers: _HeadersT
    parsed_cookies: _CookiesT
