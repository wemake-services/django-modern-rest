import typing as ty
from collections.abc import AsyncIterator, Mapping
from http import HTTPStatus

from django.http import HttpResponseBase
from typing_extensions import TypeVar, override

from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.endpoint import Endpoint
from dmr.internal.types import call_init_subclass
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, default_renderer, resolve_setting
from dmr.sse.metadata import SSE
from dmr.sse.renderer import SSERenderer
from dmr.sse.stream import SSEStreamingResponse
from dmr.sse.validation import StreamValidator
from dmr.validation.response import ValidatedModification


class _SSEEndpoint(Endpoint):
    __slots__ = ()

    @override
    def _pass_existing_response(
        self,
        response: HttpResponseBase,
    ) -> HttpResponseBase:
        # TODO: validate this before?
        assert isinstance(response, SSEStreamingResponse)
        validate_events = (
            response.validate_events or self.metadata.validate_responses
        )
        if validate_events:
            response.stream_validator = StreamValidator(
                self._resolve_event_model(response),
                response.serializer,
            )

        return response

    @override
    def _build_new_response(
        self,
        controller: Controller[BaseSerializer],
        validated: ValidatedModification,
    ) -> HttpResponseBase:
        assert isinstance(controller, SSEController)
        return self._pass_existing_response(
            controller.to_sse_response(
                validated.raw_data,
                status_code=validated.status_code,
                headers=validated.headers,
                cookies=validated.cookies,
            ),
        )

    def _resolve_event_model(self, response: HttpResponseBase) -> ty.Any:
        try:
            return self.metadata.responses[
                HTTPStatus(response.status_code)
            ].return_type
        except (KeyError, ValueError):
            # This can happen if `validate_responses` is `False`,
            # or when `status_code` is custom.
            return ty.Any


_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)


class SSEController(Controller[_SerializerT_co]):
    """
    .. danger::

        WSGI handers do not support streaming responses, including SSE,
        by default. You would need to use ASGI handler for SSE endpoints.

        We allow running SSE during ``settings.DEBUG`` builds for debugging.
        But, in production we will raise :exc:`RuntimeError`
        when WSGI handler will be detected used together with SSE.
    """

    is_stream = True
    # Custom attributes for the streaming responses:
    sse_streaming_response_cls: ty.ClassVar[type[SSEStreamingResponse]] = (
        SSEStreamingResponse
    )
    endpoint_cls = _SSEEndpoint

    @override
    def __init_subclass__(cls) -> None:
        serializer = cls._infer_serializer()
        if serializer is None:
            return  # this is an abstract controller

        renderers = cls.renderers or resolve_setting(Settings.renderes)
        cls.renderers = (
            cls.stream_renderer(),
            *(cls.renderers or resolve_setting(Settings.renderes)),
        )

        # Now we have everything and we can create `api_endpoints`:
        call_init_subclass(Controller, cls)

        # TODO: run validation

    @classmethod
    def stream_renderer(cls) -> Renderer:
        return SSERenderer(cls.serializer, default_renderer)

    def to_sse_response(  # TODO: to_stream
        self,
        streaming_content: AsyncIterator[SSE],
        *,
        status_code: HTTPStatus = HTTPStatus.OK,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        validate_events: bool | None = None,
    ) -> SSEStreamingResponse:
        streaming_response = self.sse_streaming_response_cls(
            streaming_content,
            headers=headers,
            status_code=status_code,
            serializer=self.serializer,
            regular_renderer=self.regular_renderer,
            sse_renderer=self.sse_renderer,
            validate_events=validate_events,
        )
        for cookie_key, cookie in (cookies or {}).items():
            streaming_response.set_cookie(
                cookie_key,
                **cookie.as_dict(),
            )
        return streaming_response
