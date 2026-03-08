import dataclasses
from collections.abc import AsyncIterator, Mapping
from types import AsyncGeneratorType
from typing import (
    Any,
    Generic,
    Literal,
    NamedTuple,
    final,
    get_args,
    overload,
)

from typing_extensions import TypeVar

from dmr.cookies import NewCookie
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.types import Empty, EmptyObj, parse_return_annotation

_DataT_co = TypeVar('_DataT_co', covariant=True)


@final
@dataclasses.dataclass(init=False)
class SSEvent(Generic[_DataT_co]):
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

    data: _DataT_co  # type: ignore[misc]  # noqa: WPS110
    event: str | None = dataclasses.field(default=None, kw_only=True)
    id: int | str | None = dataclasses.field(default=None, kw_only=True)
    retry: int | None = dataclasses.field(default=None, kw_only=True)
    comment: str | None = dataclasses.field(default=None, kw_only=True)

    @overload
    def __init__(
        self: 'SSEvent[bytes]',
        data: bytes,
        *,
        event: str | None = None,
        id: int | str | None = None,
        retry: int | None = None,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None: ...

    @overload
    def __init__(
        self,
        data: _DataT_co,
        *,
        event: str | None = None,
        id: int | str | None = None,
        retry: int | None = None,
        comment: str | None = None,
        serialize: Literal[True] = True,
    ) -> None: ...

    def __init__(
        self: 'SSEvent[_DataT_co | bytes]',
        data: _DataT_co | bytes,
        *,
        event: str | None = None,
        id: int | str | None = None,  # noqa: A002
        retry: int | None = None,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None:
        if not serialize and not isinstance(data, bytes):
            raise ValueError(
                f'data must be an instance of "bytes", not {type(data)}, '
                'when serialize=False',
            )

        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment
        self._serialize = serialize

    @property
    def serialize(self) -> bool:
        return self._serialize


_EventT = TypeVar('_EventT')


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEResponse(Generic[_EventT]):
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
        event_model: Optional explicit event model to be used
            for the runtime validation of events' data.

    """

    streaming_content: AsyncIterator[SSEvent[_EventT]]
    headers: Mapping[str, str] | None = None
    cookies: Mapping[str, NewCookie] | None = None
    event_model: Any | Empty = EmptyObj  # `None` can be a valid model

    def resolve_event_model(self) -> Any:
        if self.event_model is EmptyObj:
            inferred_model = self._infer_model()
            if inferred_model is EmptyObj:
                raise UnsolvableAnnotationsError(
                    f'Cannot resolve event model for {self.streaming_content}, '
                    'pass `event_model=` parameter directly for validation',
                )
            return inferred_model
        return self.event_model

    def _infer_model(self) -> Any | Empty:
        return_annotation = self._infer_return_annotaiton()
        if return_annotation is EmptyObj:
            return return_annotation
        # We expect return annotation to be: `AsyncIterator[SSEvent[Model]]`.
        # We need `SSEvent[Model]` from it.
        try:
            return get_args(return_annotation)[0]
        except Exception:
            return EmptyObj

    def _infer_return_annotaiton(self) -> Any | Empty:
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
