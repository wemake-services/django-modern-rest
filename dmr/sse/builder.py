import dataclasses
from collections.abc import (
    Awaitable,
    Callable,
    Sequence,
)
from http import HTTPStatus
from typing import (
    Any,
    ClassVar,
)

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from typing_extensions import TypeVar, override

from dmr.components import Cookies, Headers, Path, Query
from dmr.controller import Controller
from dmr.endpoint import validate
from dmr.headers import HeaderSpec
from dmr.internal.negotiation import force_request_renderer
from dmr.metadata import EndpointMetadata, ResponseSpec
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.settings import default_renderer
from dmr.sse.metadata import SSEContext, SSEResponse, SSEData
from dmr.sse.stream import SSEStreamingResponse
from dmr.sse.renderer import SSERenderer


class _SSEMetadata(EndpointMetadata):
    default_renderer: ClassVar[Renderer]

    @override
    def collect_response_specs(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: dict[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        all_responses = super().collect_response_specs(
            controller_cls,
            existing_responses,
        )
        return [
            dataclasses.replace(
                response,
                limit_to_content_types={self.default_renderer.content_type},
            )
            for response in all_responses
        ]


_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_PathT = TypeVar('_PathT', default=None)
_QueryT = TypeVar('_QueryT', default=None)
_HeadersT = TypeVar('_HeadersT', default=None)
_CookiesT = TypeVar('_CookiesT', default=None)


def sse(
    serializer: type[_SerializerT],
    *,
    path: type[Path[_PathT]] | None = None,
    query: type[Query[_QueryT]] | None = None,
    headers: type[Headers[_HeadersT]] | None = None,
    cookies: type[Cookies[_CookiesT]] | None = None,
    response_spec: ResponseSpec | None = None,
    extra_responses: Sequence[ResponseSpec] = (),
    validate_responses: bool = True,
    validate_events: bool | None = None,
    regular_renderer: Renderer | None = None,
    sse_renderer: SSERenderer | None = None,
    sse_streaming_response_cls: type[
        SSEStreamingResponse
    ] = SSEStreamingResponse,
    metadata_cls: type[EndpointMetadata] = _SSEMetadata,
) -> Callable[
    [
        Callable[
            [
                HttpRequest,
                Renderer,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse],
        ],
    ],
    type[Controller[_SerializerT]],
]:
    # All these new variables are needed, because `mypy` can't properly
    # resolved narrower types for them:
    if validate_events is None:
        resolved_validate_events = validate_responses
    else:
        resolved_validate_events = validate_events

    resolved_renderer = regular_renderer or default_renderer
    resolved_sse_renderer = sse_renderer or SSERenderer()

    if response_spec is None:
        resolved_response_spec = ResponseSpec(
            SSEData,
            status_code=HTTPStatus.OK,
            headers={
                'Cache-Control': HeaderSpec(),
                'Connection': HeaderSpec(required=not settings.DEBUG),
                'X-Accel-Buffering': HeaderSpec(),
            },
            limit_to_content_types={resolved_sse_renderer.content_type},
        )
    else:
        resolved_response_spec = response_spec

    modified_metadata_cls = type(
        '_LimitedSSEMetadata',
        (metadata_cls,),
        {'default_renderer': resolved_renderer},
    )

    def decorator(
        func: Callable[
            [
                HttpRequest,
                Renderer,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse],
        ],
        /,
    ) -> type[Controller[_SerializerT]]:

        return _build_controller(
            func,
            serializer=serializer,
            path=path,
            query=query,
            headers=headers,
            cookies=cookies,
            response_spec=resolved_response_spec,
            extra_responses=extra_responses,
            validate_responses=validate_responses,
            validate_events=resolved_validate_events,
            regular_renderer=resolved_renderer,
            sse_renderer=resolved_sse_renderer,
            sse_streaming_response_cls=sse_streaming_response_cls,
            metadata_cls=modified_metadata_cls,
        )

    return decorator


def _build_controller(
    func: Callable[
            [
                HttpRequest,
                Renderer,
                SSEContext[_PathT, _QueryT, _HeadersT, _CookiesT],
            ],
            Awaitable[SSEResponse],
        ],
    /,
    serializer: type[_SerializerT],
    *,
    path: type[Path[_PathT]] | None,
    query: type[Query[_QueryT]] | None,
    headers: type[Headers[_HeadersT]] | None,
    cookies: type[Cookies[_CookiesT]] | None,
    response_spec: ResponseSpec,
    extra_responses: Sequence[ResponseSpec] = (),
    validate_responses: bool = True,
    validate_events: bool,
    regular_renderer: Renderer,
    sse_renderer: SSERenderer,
    sse_streaming_response_cls: type[SSEStreamingResponse],
    metadata_cls: type[EndpointMetadata],
) -> type[Controller[_SerializerT]]:
    class SSEController(
        Controller[serializer],  # type: ignore[valid-type]
        *filter(None, [path, query, headers, cookies]),  # type: ignore[misc]
    ):
        @override
        def to_error(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponse:
            force_request_renderer(self.request, regular_renderer)
            return super().to_error(*args, **kwargs)

        @validate(
            response_spec,
            *extra_responses,
            renderers=[sse_renderer, regular_renderer],
            validate_responses=validate_responses,
            metadata_cls=metadata_cls,
        )
        async def get(self) -> SSEStreamingResponse:
            context = SSEContext(
                self.parsed_path if path else None,
                self.parsed_query if query else None,
                self.parsed_headers if headers else None,
                self.parsed_cookies if cookies else None,
            )

            # Now, everything is ready to send SSE events:
            return self.build_sse_streaming_response(
                await func(
                    self.request,
                    regular_renderer,
                    context,  # type: ignore[arg-type]
                ),
            )

        def build_sse_streaming_response(
            self,
            response: SSEResponse,
        ) -> SSEStreamingResponse:
            streaming_response = sse_streaming_response_cls(
                response.streaming_content,
                serializer=serializer,
                regular_renderer=regular_renderer,
                sse_renderer=sse_renderer,
                event_schema=response_spec.return_type,
                headers=response.headers,
                validate_events=validate_events,
            )
            if response.cookies:
                for cookie_key, cookie in response.cookies.items():
                    streaming_response.set_cookie(
                        cookie_key,
                        **cookie.as_dict(),
                    )
            return streaming_response

    return SSEController
