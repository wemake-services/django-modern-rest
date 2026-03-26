import dataclasses
from collections.abc import AsyncIterator, Mapping, Set
from http import HTTPStatus
from typing import Any, Generic, Literal, NamedTuple, Protocol, final, overload

from typing_extensions import TypeVar, override

from dmr.cookies import NewCookie
from dmr.headers import HeaderSpec
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.negotiation import ContentType
from dmr.openapi import OpenAPIContext
from dmr.openapi.objects import Response
from dmr.serializer import BaseSerializer
from dmr.sse.validation import check_event_field

_DataT_co = TypeVar('_DataT_co', covariant=True)


class SSE(Protocol):
    """
    Basic interface for all possible SSE implementations.

    We don't force users to use our default implementation, moreover,
    we encourage them to create their own event ADT and models.
    """

    data: Any = None
    event: Any = None
    id: Any = None
    retry: Any = None
    comment: Any = None

    @property
    def should_serialize_data(self) -> bool:
        """Should we serialize the data attribute or return it as is?"""
        raise NotImplementedError


@final
@dataclasses.dataclass(init=False)
class SSEvent(Generic[_DataT_co]):
    """
    Default implementation for the Server Sent Event.

    All parameters are optional, but at least one is required.

    Attributes:
        data: Event payload.
        event: Event type.
        id: Unique event's identification.
        retry: The reconnection time.
        comment: Comment about the event.

    .. note::

        It is recommended for end users to define their own types
        that will be type-safe and will have the correct schema.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#fields

    """

    # Fields declaration, `__init__` method is customized further:
    data: _DataT_co  # type: ignore[misc, unused-ignore]
    # ^^ for some reason 3.11 and 3.12 does not report a mypy error here.
    event: str | None = None
    id: int | str | None = None
    retry: int | None = None
    comment: str | None = None

    @overload
    def __init__(
        self: 'SSEvent[None]',
        data: None = None,
        *,
        event: str,
        id: int | str | None = None,
        retry: int | None = None,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None: ...

    @overload
    def __init__(
        self: 'SSEvent[None]',
        data: None = None,
        *,
        event: str | None = None,
        id: int | str,
        retry: int | None = None,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None: ...

    @overload
    def __init__(
        self: 'SSEvent[None]',
        data: None = None,
        *,
        event: str | None = None,
        id: int | str | None = None,
        retry: int,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None: ...

    @overload
    def __init__(
        self: 'SSEvent[None]',
        data: None = None,
        *,
        event: str | None = None,
        id: int | str | None = None,
        retry: int | None = None,
        comment: str,
        serialize: bool = True,
    ) -> None: ...

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

    def __init__(  # noqa: WPS211
        self: 'SSEvent[Any]',
        data: _DataT_co | bytes | None = None,
        *,
        event: str | None = None,
        id: int | str | None = None,  # noqa: A002
        retry: int | None = None,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None:
        """Initialize and validate the default SSE event."""
        if not serialize and not isinstance(data, bytes):
            raise ValueError(
                f'data must be an instance of "bytes", not {type(data)}, '
                'when serialize=False',
            )
        if (
            data is None  # noqa: WPS222
            and event is None
            and id is None
            and retry is None
            and comment is None
        ):
            raise ValueError('At least one event field must be non-None')

        # Check null byte and new lines:
        check_event_field(id, field_name='id')
        check_event_field(event, field_name='event')

        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment
        self._serialize = serialize

    @property
    def should_serialize_data(self) -> bool:
        """
        Should we serialize ``data`` attribute with the serializer?

        Serializes by default. When *serialize* is ``False``,
        *data* can only be ``bytes``.
        """
        return self._serialize


@dataclasses.dataclass(slots=True, frozen=True)
class SSEResponseSpec(ResponseSpec):
    """Subclass to represent the SSE response specification."""

    status_code: Literal[HTTPStatus.OK] = dataclasses.field(
        kw_only=True,
        default=HTTPStatus.OK,
    )
    headers: Mapping[str, 'HeaderSpec'] | None = dataclasses.field(
        kw_only=True,
        default_factory=lambda: {
            'Cache-Control': HeaderSpec(),
            'X-Accel-Buffering': HeaderSpec(),
            # wsgi cannot provide `Connection` header in `DEBUG`:
            'Connection': HeaderSpec(skip_validation=True),
        },
    )
    limit_to_content_types: Set[str] | None = dataclasses.field(
        kw_only=True,
        default_factory=lambda: {ContentType.event_stream},
    )

    @override
    def get_schema(
        self,
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: OpenAPIContext,
    ) -> Response:
        """Customizes how response's schemas are rendered."""
        return context.generators.response.get_schema(
            self,
            metadata,
            serializer,
            context,
            schema_field_name='item_schema',
            # Despite the fact that it looks like a response,
            # produced events are not regular responses.
            used_for_response=False,
        )


_EventT_co = TypeVar('_EventT_co', bound=SSE, covariant=True)


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SSEResponse(Generic[_EventT_co]):
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

    streaming_content: AsyncIterator[_EventT_co]
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
