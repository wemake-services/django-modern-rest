# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false
import abc
from collections.abc import AsyncIterator, Mapping
from http import HTTPStatus
from typing import Any, ClassVar, TypeVar

from django.http import HttpResponseBase
from typing_extensions import override

from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.endpoint import Endpoint
from dmr.internal.types import call_init_subclass
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
    def _pass_existing_response(
        self,
        controller: 'Controller[BaseSerializer]',
        response: HttpResponseBase,
    ) -> HttpResponseBase:
        # TODO: validate this before?
        if isinstance(response, StreamingResponse):
            # for mypy: it is required by the contract.
            assert isinstance(controller, StreamingController)  # noqa: S101
            if self.metadata.validate_events:
                response.streaming_validator = (
                    controller.streaming_validator_cls(
                        self._resolve_event_model(response),
                        response.serializer,
                    )
                )
        return super()._pass_existing_response(controller, response)

    @override
    def _build_new_response(
        self,
        controller: 'Controller[BaseSerializer]',
        validated: 'ValidatedModification',
    ) -> HttpResponseBase:
        # for mypy: we only use `_StreamingEndpoint` with `StreamingController`
        assert isinstance(controller, StreamingController)  # noqa: S101
        return self._pass_existing_response(
            controller,
            controller.to_stream(
                validated.raw_data,
                status_code=validated.status_code,
                headers=validated.headers,
                cookies=validated.cookies,
            ),
        )

    def _resolve_event_model(self, response: HttpResponseBase) -> Any:
        try:
            return self.metadata.responses[
                HTTPStatus(response.status_code)
            ].return_type
        except (KeyError, ValueError):
            # This can happen if `validate_responses` is `False`,
            # or when `status_code` is custom.
            return Any


_SerializerT_co = TypeVar(
    '_SerializerT_co',
    bound=BaseSerializer,
    covariant=True,
)

_EventT = TypeVar('_EventT')


class StreamingController(Controller[_SerializerT_co]):
    """
    Base class for all streaming controllers.

    .. danger::

        WSGI handers do not support streaming responses,
        by default. You would need to use ASGI handler for streaming endpoints.

        We allow running streaming during
        ``settings.DEBUG`` builds for debugging.
        But, in production we will raise :exc:`RuntimeError`
        when WSGI handler will be detected used together with SSE.
    """

    streaming = True
    endpoint_cls = _StreamingEndpoint

    # Set in `__init_subclasses__`:
    streaming_renderer: ClassVar[StreamingRenderer]

    # Custom attributes to be set in subclasses:
    streaming_response_cls: ClassVar[type[StreamingResponse]]
    streaming_validator_cls: ClassVar[type[StreamingValidator]]

    @override
    def __init_subclass__(cls) -> None:
        serializer = cls._infer_serializer()
        if serializer is None:
            return  # this is an abstract controller

        cls.streaming_renderer = cls.streaming_renderer(serializer)
        cls.renderers = (
            cls.streaming_renderer,
            *(cls.renderers or resolve_setting(Settings.renderers)),
        )

        # Now we have everything and we can create `api_endpoints`:
        call_init_subclass(Controller, cls)
        # TODO: run extra validation?

    @classmethod
    @abc.abstractmethod
    def streaming_renderer(
        cls,
        serializer: type[_SerializerT_co],
    ) -> StreamingRenderer:
        """Returns the streaming renderer."""

    def to_stream(
        self,
        streaming_content: AsyncIterator[Any],
        *,
        status_code: HTTPStatus = HTTPStatus.OK,
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        validate_events: bool | None = None,
    ) -> StreamingResponse:
        streaming_response = self.streaming_response_cls(
            streaming_content,
            headers=headers,
            status_code=status_code,
            serializer=self.serializer,
            regular_renderer=default_renderer,
            streaming_renderer=self.streaming_renderer,
        )
        for cookie_key, cookie in (cookies or {}).items():
            streaming_response.set_cookie(
                cookie_key,
                **cookie.as_dict(),
            )
        return streaming_response
