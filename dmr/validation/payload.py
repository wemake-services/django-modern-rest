import dataclasses
from collections.abc import Callable, Mapping, Sequence, Set
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, final

from typing_extensions import Sentinel

from dmr.cookies import CookieSpec, NewCookie
from dmr.errors import AsyncErrorHandler, SyncErrorHandler
from dmr.headers import HeaderSpec, NewHeader
from dmr.internal.types import StrOrPromise
from dmr.metadata import ResponseSpec
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.settings import HttpSpec
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Link,
        Reference,
        SecurityRequirement,
        Server,
    )
    from dmr.security.base import AsyncAuth, SyncAuth
    from dmr.serializer import BaseSerializer
    from dmr.throttling import AsyncThrottle, SyncThrottle


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True, init=False)
class _BasePayload:
    # OpenAPI stuff:
    summary: StrOrPromise | Sentinel | None
    description: StrOrPromise | Sentinel | None
    tags: Sequence[str] | Sentinel | None
    operation_id: str | Sentinel
    deprecated: bool
    security: Sequence['SecurityRequirement'] | Sentinel | None
    external_docs: 'ExternalDocumentation | Sentinel'
    callbacks: Mapping[str, 'Callback | Reference'] | Sentinel
    servers: Sequence['Server'] | Sentinel | None
    ignore_from_spec: bool | Sentinel

    # Common fields:
    validate_responses: bool | Sentinel
    exclude_validate_responses: Set[HTTPStatus] | Sentinel | None
    semantic_schema: bool | Sentinel
    semantic_responses: bool | Sentinel
    exclude_semantic_responses: Set[HTTPStatus] | Sentinel | None
    semantic_auth: bool | Sentinel
    exclude_semantic_auth: Set[str] | Sentinel | None
    validate_events: bool | Sentinel
    error_handler: SyncErrorHandler | AsyncErrorHandler | Sentinel
    no_validate_http_spec: Set[HttpSpec] | Sentinel | None
    parsers: Sequence[Parser] | Sentinel
    renderers: Sequence[Renderer] | Sentinel
    validate_negotiation: bool | Sentinel
    auth: Sequence['SyncAuth'] | Sequence['AsyncAuth'] | Sentinel | None
    throttling: (
        Sequence['SyncThrottle'] | Sequence['AsyncThrottle'] | Sentinel | None
    )
    throttling_allow_unsafe_cache: bool | Sentinel | None


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ValidateEndpointPayload(_BasePayload):
    """Payload created by ``@validate``."""

    responses: list[ResponseSpec]

    @classmethod
    def implicit(cls) -> 'ValidateEndpointPayload':
        """
        Create a payload for endpoints that return ``HttpResponse``.

        Such endpoints do not have to use ``@validate`` explicitly,
        when responses are defined on the controller or settings level.
        All values are the same as ``@validate`` defaults.
        """
        return cls(
            responses=[],
            summary=EMPTY,
            description=EMPTY,
            tags=EMPTY,
            operation_id=EMPTY,
            deprecated=False,
            security=EMPTY,
            external_docs=EMPTY,
            callbacks=EMPTY,
            servers=EMPTY,
            ignore_from_spec=EMPTY,
            validate_responses=EMPTY,
            exclude_validate_responses=EMPTY,
            semantic_schema=EMPTY,
            semantic_responses=EMPTY,
            exclude_semantic_responses=EMPTY,
            semantic_auth=EMPTY,
            exclude_semantic_auth=EMPTY,
            validate_events=EMPTY,
            error_handler=EMPTY,
            no_validate_http_spec=EMPTY,
            parsers=EMPTY,
            renderers=EMPTY,
            validate_negotiation=EMPTY,
            auth=EMPTY,
            throttling=EMPTY,
            throttling_allow_unsafe_cache=EMPTY,
        )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModifyEndpointPayload(_BasePayload):
    """Payload created by ``@modify``."""

    responses: Sequence[ResponseSpec] | Sentinel | None
    status_code: HTTPStatus | Sentinel
    # Headers and cookies can be set via a middleware
    # after a response itself is formed. We need a way to describe this.
    # That's why `HeaderSpec` and `CookieSpec` are allowed.
    headers: Mapping[str, NewHeader | HeaderSpec] | Sentinel
    cookies: Mapping[str, NewCookie | CookieSpec] | Sentinel

    # OpenAPI metadata:
    response_description: str | Sentinel
    links: Mapping[str, 'Link | Reference'] | Sentinel


#: Alias for different payload types:
Payload: TypeAlias = ValidateEndpointPayload | ModifyEndpointPayload | None


_PayloadOrLazy: TypeAlias = (
    Callable[[type['Controller[BaseSerializer]']], Callable[..., Any]] | Payload
)


@dataclasses.dataclass(slots=True, frozen=True)
class PayloadBuilder:
    """
    Builds the payload from the endpoint function and the controller class.

    .. versionadded:: 0.15.0
    """

    func: Callable[..., Any]

    # Class-level API:
    _payload_key: ClassVar[str] = '__dmr_payload__'

    def __call__(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> Payload:
        """Processes the callable payloads from ``modify.lazy`` and others."""
        payload: _PayloadOrLazy = getattr(
            self.func,
            self._payload_key,
            None,
        )
        # `modify.lazy` and `validate.lazy` can provide callable payloads:
        if callable(payload):
            return getattr(  # type: ignore[no-any-return]
                payload(controller_cls)(
                    # What happens here? We need to extract `__dmr_payload__`
                    # from a function that our decorators attach it to.
                    # But, we don't want to over-write the original function's
                    # payload metadata. So, we create a throw-away one.
                    lambda: ...,
                ),
                self._payload_key,
            )
        return payload
