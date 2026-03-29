# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
import abc
from collections.abc import AsyncIterator, Iterable, Mapping
from http import HTTPStatus
from typing import Any, ClassVar, TypeVar, cast

from django.http import HttpResponseBase
from typing_extensions import override

from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.endpoint import Endpoint
from dmr.internal.types import call_init_subclass
from dmr.negotiation import request_renderer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, default_renderer, resolve_setting
from dmr.streaming.metadata import StreamResponseModification
from dmr.streaming.renderer import StreamingRenderer
from dmr.streaming.stream import StreamingResponse
from dmr.streaming.validation import StreamingValidator
from dmr.validation.response import ValidatedModification


class _StreamingEndpoint(Endpoint):
    response_modification_cls = StreamResponseModification

    __slots__ = ()

    @override
    def _build_new_response(
        self,
        controller: 'Controller[BaseSerializer]',
        validated: 'ValidatedModification',
    ) -> HttpResponseBase:
        # for mypy: we only use `_StreamingEndpoint` with `StreamingController`
        assert isinstance(controller, StreamingController)  # noqa: S101
        return controller.to_stream(
            validated.raw_data,
            status_code=validated.status_code,
            headers=validated.headers,
            cookies=validated.cookies,
        )


_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)

_EventT = TypeVar('_EventT')


class StreamingController(Controller[_SerializerT_co]):
    """
    Base class for all streaming controllers.

    It can be used directly, but the most use-cases will be fine
    with just using the specific streaming protocol.
    """

    streaming = True
    endpoint_cls = _StreamingEndpoint

    # Customizable attributes for subclasses:
    streaming_ping_seconds: ClassVar[float | None] = None
    """
    Optional ping keep alive event support.

    Some servers might close long living connections with no activity.
    Specify number in second how long should we wait between events.
    If we wait longer, we will send a ping event.
    The payload of the ping event is defined in
    :meth:`~dmr.streaming.controller.StreamingController.ping_event`.

    By default it is disabled. It is only enabled in the SSE streaming.
    """

    streaming_response_cls: ClassVar[type[StreamingResponse]] = (
        StreamingResponse
    )
    """Streaming response type to customize."""

    @override
    def __init_subclass__(cls) -> None:
        serializer = cls._infer_serializer()
        if serializer is None:
            return  # this is an abstract controller

        cls.renderers = (
            *cls.streaming_renderers(serializer),
            *(cls.renderers or resolve_setting(Settings.renderers)),
        )

        # Now we have everything and we can create `api_endpoints`:
        call_init_subclass(Controller, cls)
        # TODO: run extra validation?
        # TODO: validate that endpoints can't contain `yield event` themself.

    @classmethod
    @abc.abstractmethod
    def streaming_renderers(
        cls,
        serializer: type[_SerializerT_co],  # pyright: ignore[reportGeneralTypeIssues]
    ) -> Iterable[StreamingRenderer]:
        """Returns the streaming renderer."""

    async def handle_event_error(self, exc: Exception) -> Any:
        """
        Error handler for the events.

        Is called when the :class:`~dmr.streaming.stream.StreamingResponse`
        is iterated in the ASGI handler.
        """
        raise exc from None

    def to_stream(  # noqa: WPS211
        self,
        streaming_content: AsyncIterator[Any],
        *,
        status_code: HTTPStatus = HTTPStatus.OK,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        validate_events: bool | None = None,
        regular_renderer: Renderer | None = None,
        streaming_renderer: StreamingRenderer | None = None,
        streaming_validator: StreamingValidator | None = None,
    ) -> StreamingResponse:
        """Convert streaming content to a streaming response."""
        # We are sure that it is a `StreamingRenderer` at this point
        streaming_renderer = cast(  # type: ignore[assignment]
            StreamingResponse,  # TODO: provide a new api?
            streaming_renderer or request_renderer(self.request),
        )
        # for mypy: we are sure it is not `None` here.
        assert streaming_renderer is not None  # noqa: S101

        streaming_response = self.streaming_response_cls(
            streaming_content,
            controller=self,
            headers=headers,
            status_code=status_code,
            regular_renderer=regular_renderer or default_renderer,
            streaming_renderer=streaming_renderer,
            streaming_validator=(
                streaming_validator
                or streaming_renderer.streaming_validator_cls.from_controller(
                    self,
                    status_code=status_code,
                )
            ),
        )
        for cookie_key, cookie in (cookies or {}).items():
            streaming_response.set_cookie(
                cookie_key,
                **cookie.as_dict(),
            )
        return streaming_response

    def ping_event(self) -> Any | None:
        """
        Return a ping event to be generated if this streaming needs it.

        By default pings are disabled for ``StreamingController`` types.
        Pings must be explicitly enabled in subclasses.

        If ``streaming_ping_seconds`` is set, this method will be called.
        """
