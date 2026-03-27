from typing import TypeVar

from typing_extensions import override

from dmr.serializer import BaseSerializer
from dmr.settings import default_renderer
from dmr.streaming.controller import StreamingController
from dmr.streaming.renderer import StreamingRenderer
from dmr.streaming.sse.renderer import SSERenderer
from dmr.streaming.sse.stream import SSEStreamingResponse
from dmr.streaming.sse.validation import SSEStreamingValidator

_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)


class SSEController(StreamingController[_SerializerT_co]):
    """
    Controller for streaming Server Sent Events (SSE).

    .. danger::

        WSGI handers do not support streaming responses, including SSE,
        by default. You would need to use ASGI handler for SSE endpoints.

        We allow running SSE during ``settings.DEBUG`` builds for debugging.
        But, in production we will raise :exc:`RuntimeError`
        when WSGI handler will be detected used together with SSE.

    """

    streaming_response_cls = SSEStreamingResponse
    streaming_validator_cls = SSEStreamingValidator

    @override
    @classmethod
    def streaming_renderer(
        cls,
        serializer: type[_SerializerT_co],
    ) -> StreamingRenderer:
        return SSERenderer(serializer, default_renderer)
