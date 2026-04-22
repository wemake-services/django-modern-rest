import dataclasses
from typing import Any, Generic, Literal, Protocol, TypeVar, final, overload

from dmr.streaming.sse.validation import check_event_field

_DataT_co = TypeVar('_DataT_co', covariant=True)


class SSE(Protocol):
    """
    Basic interface for all possible SSE implementations.

    We don't force users to use our default implementation, moreover,
    we encourage them to create their own event ADT and models.
    """

    data: Any
    event: str | None
    id: int | str | None
    retry: int | None
    comment: str | None

    @property
    def should_serialize_data(self) -> bool:
        """Should we serialize the data attribute or return it as is?"""
        raise NotImplementedError


class _SSEventSlots:
    # The only purpose of this class is to help constructing correct
    # SSEvent dataclass with the correct slots.
    # Since, `_serialize` is not listed as the dataclass field,
    # we need to set this slot by hands:
    __slots__ = ('_serialize',)


@final
@dataclasses.dataclass(init=False, slots=True)
class SSEvent(_SSEventSlots, Generic[_DataT_co]):
    """Server sent event payload."""

    # We keep the docstring short, because it is used in the schema.

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

    def __init__(
        self: 'SSEvent[Any]',
        data: _DataT_co | bytes | None = None,
        *,
        event: str | None = None,
        id: int | str | None = None,  # noqa: A002
        retry: int | None = None,
        comment: str | None = None,
        serialize: bool = True,
    ) -> None:
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
        # TODO: this also works when `validate_events` is `False`,
        # I don't think that it is correct. When `validate_events` is `False`
        # we need to trust the user to provide valid data and allow everything
        # for performance reasons.
        check_event_field(id, field_name='id')
        check_event_field(event, field_name='event')

        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.comment = comment
        self._serialize = serialize  # type: ignore[misc]

    @property
    def should_serialize_data(self) -> bool:
        """
        Should we serialize ``data`` attribute with the serializer?

        Serializes by default. When *serialize* is ``False``,
        *data* can only be ``bytes``.
        """
        return self._serialize
