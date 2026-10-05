import dataclasses
from collections.abc import Callable, Mapping, Sequence, Set
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, final

from dmr.cookies import CookieSpec, NewCookie
from dmr.errors import AsyncErrorHandler, SyncErrorHandler
from dmr.headers import HeaderSpec, NewHeader
from dmr.internal.types import EMPTY, StrOrPromise
from dmr.metadata import ResponseSpec
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.settings import HttpSpec

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.internal.endpoint import Extras
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
    summary: StrOrPromise | EMPTY | None
    description: StrOrPromise | EMPTY | None
    tags: Sequence[str] | EMPTY | None
    operation_id: str | EMPTY
    deprecated: bool | EMPTY
    security: Sequence['SecurityRequirement'] | EMPTY | None
    external_docs: 'ExternalDocumentation | EMPTY | None'
    callbacks: Mapping[str, 'Callback | Reference'] | EMPTY | None
    servers: Sequence['Server'] | EMPTY | None
    x_extensions: Mapping[str, Any] | EMPTY
    ignore_from_spec: bool | EMPTY

    # Extras:
    extras: 'Extras[Any] | EMPTY'
    extras_cls: 'type[Extras[Any]] | EMPTY'

    # Common fields:
    validate_responses: bool | EMPTY
    exclude_validate_responses: Set[HTTPStatus] | EMPTY | None
    semantic_schema: bool | EMPTY
    semantic_responses: bool | EMPTY
    exclude_semantic_responses: Set[HTTPStatus] | EMPTY | None
    semantic_auth: bool | EMPTY
    exclude_semantic_auth: Set[str] | EMPTY | None
    error_handler: SyncErrorHandler | AsyncErrorHandler | EMPTY
    no_validate_http_spec: Set[HttpSpec] | EMPTY | None
    parsers: Sequence[Parser] | EMPTY
    renderers: Sequence[Renderer] | EMPTY
    validate_negotiation: bool | EMPTY
    auth: Sequence['SyncAuth'] | Sequence['AsyncAuth'] | EMPTY | None
    throttling: (
        Sequence['SyncThrottle'] | Sequence['AsyncThrottle'] | EMPTY | None
    )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ValidateEndpointPayload(_BasePayload):
    """Payload created by ``@validate``."""

    # `EMPTY` is only used by `implicit()`, `@validate` always sets a list:
    responses: list[ResponseSpec] | EMPTY

    @classmethod
    def implicit(cls) -> 'ValidateEndpointPayload':
        """
        Create a payload for endpoints that return ``HttpResponse``.

        Such endpoints do not have to use ``@validate`` explicitly,
        when responses are defined on the controller or settings level.
        All values are the same as ``@validate`` defaults,
        except ``responses`` which is ``EMPTY`` and not an explicit ``[]``,
        so the controller and settings levels are used.
        """
        return cls(
            responses=EMPTY,
            summary=EMPTY,
            description=EMPTY,
            tags=EMPTY,
            operation_id=EMPTY,
            deprecated=EMPTY,
            security=EMPTY,
            external_docs=EMPTY,
            callbacks=EMPTY,
            servers=EMPTY,
            x_extensions=EMPTY,
            ignore_from_spec=EMPTY,
            validate_responses=EMPTY,
            exclude_validate_responses=EMPTY,
            semantic_schema=EMPTY,
            semantic_responses=EMPTY,
            exclude_semantic_responses=EMPTY,
            semantic_auth=EMPTY,
            exclude_semantic_auth=EMPTY,
            error_handler=EMPTY,
            no_validate_http_spec=EMPTY,
            parsers=EMPTY,
            renderers=EMPTY,
            validate_negotiation=EMPTY,
            auth=EMPTY,
            throttling=EMPTY,
            extras=EMPTY,
            extras_cls=EMPTY,
        )


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModifyEndpointPayload(_BasePayload):
    """Payload created by ``@modify``."""

    responses: Sequence[ResponseSpec] | EMPTY | None
    status_code: HTTPStatus | EMPTY
    # Headers and cookies can be set via a middleware
    # after a response itself is formed. We need a way to describe this.
    # That's why `HeaderSpec` and `CookieSpec` are allowed.
    headers: Mapping[str, NewHeader | HeaderSpec] | EMPTY
    cookies: Mapping[str, NewCookie | CookieSpec] | EMPTY

    # OpenAPI metadata:
    response_description: str | EMPTY
    links: Mapping[str, 'Link | Reference'] | EMPTY


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
