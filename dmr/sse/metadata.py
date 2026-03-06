import dataclasses
from collections.abc import AsyncIterator, Mapping
from functools import cached_property
from types import AsyncGeneratorType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NamedTuple,
    TypeVar,
    final,
    overload,
)

from typing_extensions import TypeVar

from dmr.cookies import NewCookie
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.types import Empty, EmptyObj, parse_return_annotation

_DataT = TypeVar('_DataT')


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEvent(Generic[_DataT]):
    """
    Server sent event.

    Attributes:
        data: Event payload.
        event: Event type.
        id: Unique event's identification.
        retry: The reconnection time.
        comment: Comment about the event.
        serialize: Custom attribute to indicate whether or not
            to serialize the passed value or to return the value as is.
            Serializes by default. When *serialize* is ``False``,
            *data* can only be ``bytes``.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#fields

    """

    data: _DataT  # noqa: WPS110
    event: str | None = dataclasses.field(default=None, kw_only=True)
    id: int | str | None = dataclasses.field(default=None, kw_only=True)
    retry: int | None = dataclasses.field(default=None, kw_only=True)
    comment: str | None = dataclasses.field(default=None, kw_only=True)
    serialize: bool = dataclasses.field(default=True, kw_only=True)

    if TYPE_CHECKING:

        @overload
        def __init__(
            self: SSEvent[bytes],
            data: bytes,
            *,
            event: str | None = None,
            id: int | str | None = None,
            retry: int | None = None,
            comment: str | None = None,
            serialize: Literal[False],
        ) -> None: ...

        @overload
        def __init__(
            self,
            data: _DataT,
            *,
            event: str | None = None,
            id: int | str | None = None,
            retry: int | None = None,
            comment: str | None = None,
            serialize: bool = True,
        ) -> None: ...

    def __post_init__(self) -> None:
        """Validates that serialize and data are correct."""
        if not self.serialize and not isinstance(self.data, bytes):
            raise ValueError(
                f'data must be an instance of "bytes", not {type(self.data)}, '
                'when serialize=False',
            )


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
        cookies: Cookies to be set on the response object.

    """

    streaming_content: AsyncIterator[SSEvent[Any]]
    headers: Mapping[str, str] | None = None
    cookies: Mapping[str, NewCookie] | None = None
    _event_model: Any | Empty = EmptyObj  # `None` can be a valid model

    @cached_property
    def event_model(self) -> Any:
        if self.event_model is EmptyObj:
            inferred_model = self._infer_model()
            if inferred_model is EmptyObj:
                raise UnsolvableAnnotationsError(
                    f'Cannot resolve event model for {self.streaming_content}, '
                    'pass `event_model=` parameter directly for validation',
                )
        return self.event_model

    def _infer_model(self) -> Any | Empty:
        # Is it `async def(): yield`?
        if isinstance(self.streaming_content, AsyncGeneratorType):
            try:
                return parse_return_annotation(
                    self.streaming_content.ag_frame.f_globals[
                        self.streaming_content.__qualname__
                    ],
                )
            except Exception:
                return EmptyObj

        # Is it an instance with `__aiter__`?
        method = getattr(self.streaming_content, '__aiter__', None)
        if method is None:
            return EmptyObj
        try:
            return parse_return_annotation(method)
        except Exception:
            return EmptyObj


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
