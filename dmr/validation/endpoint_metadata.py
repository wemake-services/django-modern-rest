import dataclasses
import inspect
import re
import warnings
from collections.abc import (
    Callable,
    ItemsView,
    Sequence,
    Set,
)
from http import HTTPMethod, HTTPStatus
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Literal,
    ParamSpec,
    TypeVar,
    assert_never,
)

from django.core.cache.backends import dummy, locmem
from django.http import HttpResponseBase
from typing_extensions import Sentinel

from dmr.components import BodyComponent
from dmr.cookies import CookieSpec, NewCookie
from dmr.exceptions import EndpointMetadataError, UnsolvableAnnotationsError
from dmr.headers import HeaderSpec, NewHeader
from dmr.internal.docstrings import resolve_summary_and_description
from dmr.internal.enums import stringify
from dmr.metadata import (
    ComponentParserSpec,
    EndpointMetadata,
    ResponseModification,
    ResponseSpec,
)
from dmr.parsers import Parser
from dmr.renderers import Renderer
from dmr.response import infer_status_code
from dmr.security.base import AsyncAuth, SyncAuth, SyncOrAsyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import HttpSpec, Settings, resolve_setting
from dmr.throttling import AsyncThrottle, SyncOrAsyncThrottle, SyncThrottle
from dmr.throttling.backends.django_cache import (
    AsyncDjangoCache,
    SyncDjangoCache,
    UnsafeCacheBackendWarning,
)
from dmr.types import EMPTY, infer_annotation, is_safe_subclass
from dmr.validation.payload import (
    ModifyEndpointPayload,
    Payload,
    ValidateEndpointPayload,
    empty_to_none,
    first_defined,
    first_set,
)

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.errors import AsyncErrorHandler, SyncErrorHandler
    from dmr.openapi.objects import Server

#: Regex expression to match allowed chars in tokens
#: For header and cookie names.
_ALLOWED_TOKENS_PATTERN: Final = re.compile(
    r'^[a-zA-Z0-9_!#$%\'*+\-.^`|~]+$',
)

#: HTTP headers that are connection-specific or
#: normally managed by the server.
#: See RFC 9110 for more details.
_FORBIDDEN_RESPONSE_HEADERS: Final = frozenset((
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
    'date',
    'server',
))

#: HTTP methods that should not have a request body according to HTTP spec.
#: These methods are: GET, HEAD, DELETE, CONNECT, TRACE.
#: See RFC 7231 for more details.
_HTTP_METHODS_WITHOUT_BODY: Final = frozenset((
    'GET',
    'HEAD',
    'DELETE',
    'CONNECT',
    'TRACE',
))

_PluggableT = TypeVar('_PluggableT', bound=Parser | Renderer)
_ItemT = TypeVar('_ItemT')
_ParamT = ParamSpec('_ParamT')


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _HttpSpecValidator:  # noqa: WPS214
    """Collects all http spec validation callbacks."""

    #: 1xx responses, 204, 205, and 304 must not have a body. RFC 9110.
    _no_response_body_statuses: ClassVar[frozenset[HTTPStatus]] = frozenset((
        HTTPStatus.NO_CONTENT,
        HTTPStatus.RESET_CONTENT,
        HTTPStatus.NOT_MODIFIED,
    ))

    metadata: EndpointMetadata

    def validate(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        self._check_http_spec_rule(
            rule=HttpSpec.header_name_syntax,
            callback=self._check_http_syntax,
            responses=responses,
            field_type='cookie',
        )

        self._check_http_spec_rule(
            rule=HttpSpec.header_name_syntax,
            callback=self._check_http_syntax,
            responses=responses,
            field_type='header',
        )

        self._check_http_spec_rule(
            rule=HttpSpec.header_name_server_managed,
            callback=self._check_header_name_server_managed,
            responses=responses,
        )

        self._check_http_spec_rule(
            rule=HttpSpec.empty_response_body,
            callback=self._check_empty_response_body,
            responses=responses,
        )

    def _check_http_spec_rule(
        self,
        rule: HttpSpec,
        callback: Callable[_ParamT, None],
        *args: _ParamT.args,
        **kwargs: _ParamT.kwargs,
    ) -> None:
        if rule not in self.metadata.no_validate_http_spec:
            callback(*args, **kwargs)

    def _check_empty_response_body(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        endpoint_name = self.metadata.endpoint_name
        # For several http status codes and successful HEAD responses,
        # no response body is allowed.
        # If you specify a return annotation other than None,
        # an EndpointMetadataError will be raised.
        for response in responses:
            if not is_safe_subclass(response.return_type, NoneType) and (
                response.status_code < HTTPStatus.OK
                or response.status_code in self._no_response_body_statuses
                or (
                    stringify(self.metadata.method).upper() == HTTPMethod.HEAD
                    and response.status_code < HTTPStatus.BAD_REQUEST
                )
            ):
                raise EndpointMetadataError(
                    f'Can only return `None` not {response.return_type} '
                    f'from an endpoint {endpoint_name!r} '
                    f'with status code {response.status_code}',
                )

    def _check_header_name_server_managed(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        endpoint_name = self.metadata.endpoint_name
        for response in responses:
            if not response.headers:
                continue

            forbidden_header = self._get_forbidden_header(
                response.headers.items(),
            )

            if forbidden_header:
                raise EndpointMetadataError(
                    f'Header {forbidden_header!r} is not allowed in responses '
                    f'from endpoint {endpoint_name!r}.',
                )

    def _check_http_syntax(
        self,
        responses: list[ResponseSpec],
        field_type: Literal['cookie', 'header'],
    ) -> None:
        names = []

        modification = self.metadata.modification

        if modification:
            names = self._get_http_field_names(
                modification,
                field_type,
            )

        for response in responses:
            response_names = self._get_http_field_names(
                response,
                field_type,
            )
            names.extend(response_names)

        invalid_name = self._check_invalid_tokens(names)

        if invalid_name:
            raise EndpointMetadataError(
                f'{field_type.capitalize()} name {invalid_name!r} '
                f'is not following http spec.',
            )

    def _get_http_field_names(
        self,
        resource: ResponseSpec | ResponseModification,
        field_type: Literal['cookie', 'header'],
    ) -> list[str]:
        attribute = getattr(resource, f'{field_type}s')

        if not attribute:
            return []

        return list(attribute.keys())

    def _check_invalid_tokens(
        self,
        names: list[str],
    ) -> str | None:
        for name in names:
            if not _ALLOWED_TOKENS_PATTERN.match(name):
                return name

        return None

    def _get_forbidden_header(
        self,
        response_headers: ItemsView[str, HeaderSpec],
    ) -> str | None:

        for header_name, header in response_headers:
            if (
                header_name.lower() in _FORBIDDEN_RESPONSE_HEADERS
                and not header.skip_validation
            ):
                return header_name
        return None


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ResponseListValidator:  # noqa: WPS214
    """Validates responses metadata."""

    metadata: EndpointMetadata
    http_spec_validator: ClassVar[type[_HttpSpecValidator]] = _HttpSpecValidator

    def __call__(
        self,
        responses: list[ResponseSpec],
    ) -> dict[HTTPStatus, ResponseSpec]:
        self._validate_unique_responses(responses)
        self._validate_header_descriptions(responses)
        self._validate_cookie_descriptions(responses)
        self._validate_http_spec(responses)
        return self._convert_responses(responses)

    def _validate_unique_responses(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        endpoint_name = self.metadata.endpoint_name
        # Now, check if we have any conflicts in responses.
        # For example: same status code, mismatching metadata.
        unique: dict[HTTPStatus, ResponseSpec] = {}
        for response in responses:
            existing_response = unique.get(response.status_code)
            if existing_response is not None and existing_response != response:
                raise EndpointMetadataError(
                    f'Endpoint {endpoint_name!r} has multiple responses '
                    f'for {response.status_code=}, but with different '
                    f'metadata: {response} and {existing_response}',
                )
            unique.setdefault(response.status_code, response)

    def _validate_header_descriptions(  # noqa: WPS231
        self,
        responses: list[ResponseSpec],
    ) -> None:
        endpoint_name = self.metadata.endpoint_name
        for response in responses:
            if response.headers is None:
                continue
            for header_name, header in response.headers.items():
                if header_name.lower() == 'set-cookie':
                    raise EndpointMetadataError(
                        f'Cannot use "Set-Cookie" header in {response}, use '
                        f'`cookies=` parameter instead in {endpoint_name!r}',
                    )
                if isinstance(header, NewHeader):  # type: ignore[unreachable]
                    raise EndpointMetadataError(
                        f'Cannot use `NewHeader` in {response} , use '
                        f'`HeaderSpec` instead in {endpoint_name!r}',
                    )

    def _validate_cookie_descriptions(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        endpoint_name = self.metadata.endpoint_name
        for response in responses:
            if response.cookies is None:
                continue
            if any(
                isinstance(cookie, NewCookie)  # pyright: ignore[reportUnnecessaryIsInstance]
                for cookie in response.cookies.values()
            ):
                raise EndpointMetadataError(
                    f'Cannot use `NewCookie` in {response} , '
                    f'use `CookieSpec` instead in {endpoint_name!r}',
                )

    def _validate_http_spec(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        """Validate that we don't violate HTTP spec."""
        self.http_spec_validator(
            metadata=self.metadata,
        ).validate(
            responses=responses,
        )

    def _convert_responses(
        self,
        all_responses: list[ResponseSpec],
    ) -> dict[HTTPStatus, ResponseSpec]:
        return {resp.status_code: resp for resp in all_responses}


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadataBuilder:  # noqa: WPS214
    """
    Validate the metadata definition.

    It is done during import-time only once, so it can be not blazing fast.
    It is better to be precise here than to be fast.

    Here we only do structure and required validation.
    All semantic validation will be performed later on.

    Metadata will NOT be considered ready after running this process.
    """

    payload: Payload
    controller_cls: type['Controller[BaseSerializer]']
    func: Callable[..., Any]
    metadata_cls: type[EndpointMetadata]
    response_modification_cls: type[ResponseModification]
    component_parsers: list[ComponentParserSpec]
    type_annotations: dict[str, Any]

    # Internal fields:
    endpoint_name: str = dataclasses.field(
        init=False,
        repr=False,
        compare=False,
    )

    def __call__(self) -> EndpointMetadata:
        """Do the validation."""
        return_annotation = _resolve_return_annotation(
            self.type_annotations,
            self.controller_cls,
            self.func,
        )
        if self.payload is None and is_safe_subclass(
            return_annotation,
            HttpResponseBase,
        ):
            object.__setattr__(
                self,
                'payload',
                ValidateEndpointPayload.implicit(),
            )
        allowed_http_methods: frozenset[str] = frozenset(
            self.controller_cls.allowed_http_methods,
        )
        method = validate_method_name(
            self.func.__name__,
            allowed_http_methods=allowed_http_methods,
        )
        self.func.__name__ = method
        object.__setattr__(self, 'endpoint_name', self._build_endpoint_name())

        self._validate_return_annotation(return_annotation)

        if isinstance(self.payload, ValidateEndpointPayload):
            return self._from_validate(
                self.payload,
                method,
                allowed_http_methods=allowed_http_methods,
            )
        if isinstance(self.payload, ModifyEndpointPayload):
            return self._from_modify(
                self.payload,
                method,
                return_annotation,
                allowed_http_methods=allowed_http_methods,
            )
        if self.payload is None:
            return self._from_raw_data(
                method,
                return_annotation,
                allowed_http_methods=allowed_http_methods,
            )
        assert_never(self.payload)

    def _from_validate(
        self,
        payload: ValidateEndpointPayload,
        method: str,
        allowed_http_methods: frozenset[str],
    ) -> EndpointMetadata:
        summary, description = self._build_description()
        throttling_before_auth, throttling_after_auth, allow_cache = (
            self._build_throttling()
        )
        return self.metadata_cls(
            endpoint_name=self.endpoint_name,
            type_annotations=self.type_annotations,
            responses={},
            method=method,
            validate_responses=self._build_validate_responses(),
            modification=None,
            error_handler=self._build_error_handler(),
            component_parsers=self.component_parsers,
            parsers=self._build_parsers(),
            renderers=self._build_renderers(),
            validate_negotiation=self._build_validate_negotiation(),
            auth=self._build_auth(),
            throttling_before_auth=throttling_before_auth,
            throttling_after_auth=throttling_after_auth,
            throttling_allow_unsafe_cache=allow_cache,
            no_validate_http_spec=self._build_no_validate_http_spec(),
            allowed_http_methods=allowed_http_methods,
            exclude_validate_responses=(
                self._build_exclude_validate_responses()
            ),
            semantic_responses=self._build_semantic_responses(),
            exclude_semantic_responses=self._build_exclude_semantic_responses(),
            validate_events=self._build_validate_events(),
            summary=summary,
            description=description,
            tags=self._build_tags(payload.tags),
            operation_id=empty_to_none(payload.operation_id),
            deprecated=payload.deprecated,
            external_docs=empty_to_none(payload.external_docs),
            callbacks=empty_to_none(payload.callbacks),
            servers=self._build_servers(payload.servers),
            ignore_from_spec=self._build_ignore_from_spec(),
        )

    def _from_modify(  # noqa: WPS210
        self,
        payload: ModifyEndpointPayload,
        method: str,
        return_annotation: Any,
        *,
        allowed_http_methods: frozenset[str],
    ) -> EndpointMetadata:
        self._validate_new_http_parts(payload)
        modification = self.response_modification_cls(
            return_type=return_annotation,
            headers=empty_to_none(payload.headers),
            cookies=empty_to_none(payload.cookies),
            status_code=(
                infer_status_code(
                    method,
                    streaming=self.controller_cls.streaming,
                )
                if isinstance(payload.status_code, Sentinel)
                else payload.status_code
            ),
            streaming=self.controller_cls.streaming,
            description=empty_to_none(payload.response_description),
            links=empty_to_none(payload.links),
        )
        summary, description = self._build_description()
        throttling_before_auth, throttling_after_auth, allow_cache = (
            self._build_throttling()
        )
        return self.metadata_cls(
            endpoint_name=self.endpoint_name,
            type_annotations=self.type_annotations,
            responses={},
            validate_responses=self._build_validate_responses(),
            method=method,
            modification=modification,
            error_handler=self._build_error_handler(),
            component_parsers=self.component_parsers,
            parsers=self._build_parsers(),
            renderers=self._build_renderers(),
            validate_negotiation=self._build_validate_negotiation(),
            auth=self._build_auth(),
            throttling_before_auth=throttling_before_auth,
            throttling_after_auth=throttling_after_auth,
            throttling_allow_unsafe_cache=allow_cache,
            no_validate_http_spec=self._build_no_validate_http_spec(),
            allowed_http_methods=allowed_http_methods,
            exclude_validate_responses=(
                self._build_exclude_validate_responses()
            ),
            semantic_responses=self._build_semantic_responses(),
            exclude_semantic_responses=self._build_exclude_semantic_responses(),
            validate_events=self._build_validate_events(),
            summary=summary,
            description=description,
            tags=self._build_tags(payload.tags),
            operation_id=empty_to_none(payload.operation_id),
            deprecated=payload.deprecated,
            external_docs=empty_to_none(payload.external_docs),
            callbacks=empty_to_none(payload.callbacks),
            servers=self._build_servers(payload.servers),
            ignore_from_spec=self._build_ignore_from_spec(),
        )

    def _from_raw_data(  # noqa: WPS210
        self,
        method: str,
        return_annotation: Any,
        *,
        allowed_http_methods: frozenset[str],
    ) -> EndpointMetadata:
        modification = self.response_modification_cls(
            return_type=return_annotation,
            status_code=infer_status_code(
                method,
                streaming=self.controller_cls.streaming,
            ),
            headers=None,
            cookies=None,
            streaming=self.controller_cls.streaming,
            description=None,
            links=None,
        )
        summary, description = self._build_description()
        throttling_before_auth, throttling_after_auth, allow_cache = (
            self._build_throttling()
        )
        return self.metadata_cls(
            endpoint_name=self.endpoint_name,
            type_annotations=self.type_annotations,
            responses={},
            validate_responses=self._build_validate_responses(),
            method=method,
            modification=modification,
            error_handler=None,
            component_parsers=self.component_parsers,
            parsers=self._build_parsers(),
            renderers=self._build_renderers(),
            validate_negotiation=self._build_validate_negotiation(),
            auth=self._build_auth(),
            throttling_before_auth=throttling_before_auth,
            throttling_after_auth=throttling_after_auth,
            throttling_allow_unsafe_cache=allow_cache,
            no_validate_http_spec=self._build_no_validate_http_spec(),
            allowed_http_methods=allowed_http_methods,
            exclude_validate_responses=(
                self._build_exclude_validate_responses()
            ),
            semantic_responses=self._build_semantic_responses(),
            exclude_semantic_responses=self._build_exclude_semantic_responses(),
            validate_events=self._build_validate_events(),
            summary=summary,
            description=description,
            tags=self._build_tags(EMPTY),
            operation_id=None,
            deprecated=False,
            external_docs=None,
            callbacks=None,
            servers=None,
            ignore_from_spec=self._build_ignore_from_spec(),
        )

    def _build_endpoint_name(self) -> str:
        controller_name = self.controller_cls.__qualname__
        func_name = self.func.__name__  # `__qualname__` can be different
        return f'{controller_name}.{func_name}'

    def _build_parsers(self) -> dict[str, Parser]:
        return self._build_pluggables(
            'parser',
            self.payload.parsers if self.payload else EMPTY,
            self.controller_cls.parsers,
            resolve_setting(Settings.parsers),
        )

    def _build_renderers(self) -> dict[str, Renderer]:
        return self._build_pluggables(
            'renderer',
            self.payload.renderers if self.payload else EMPTY,
            self.controller_cls.renderers,
            resolve_setting(Settings.renderers),
        )

    def _build_pluggables(
        self,
        kind: str,
        *layers: Sequence[_PluggableT] | Sentinel | None,
    ) -> dict[str, _PluggableT]:
        pluggables = first_defined(*layers)
        if pluggables is None or isinstance(pluggables, Sentinel):
            # Settings is the last place we look at, it must be present:
            raise EndpointMetadataError(
                f'{self.endpoint_name!r} must have at least one {kind} '
                'configured in settings',
            )
        return {
            pluggable.content_type: self._check_supported(pluggable)
            for pluggable in pluggables
        }

    def _check_supported(
        self,
        pluggable: _PluggableT,
    ) -> _PluggableT:
        if self.controller_cls.serializer.is_supported(pluggable):
            return pluggable
        raise EndpointMetadataError(
            f'{self.endpoint_name!r} serializer does not support {pluggable!r}',
        )

    def _build_validate_negotiation(self) -> bool:
        settings_value: bool | Sentinel = resolve_setting(
            Settings.validate_negotiation,
        )
        validate_negotiation = first_set(
            self.payload.validate_negotiation if self.payload else EMPTY,
            self.controller_cls.validate_negotiation,
            settings_value,
        )
        if isinstance(validate_negotiation, Sentinel):
            return self._build_validate_responses()
        return validate_negotiation

    def _build_servers(
        self,
        payload_servers: Sequence['Server'] | Sentinel | None,
    ) -> list['Server'] | None:
        servers = empty_to_none(payload_servers)
        return None if servers is None else list(servers)

    def _build_auth(  # noqa: WPS231
        self,
    ) -> list[SyncAuth | AsyncAuth] | None:
        base_type = (
            AsyncAuth if inspect.iscoroutinefunction(self.func) else SyncAuth
        )
        auth = first_defined(
            self.payload.auth if self.payload else EMPTY,
            self.controller_cls.auth,
        )
        if auth is None:
            return None  # explicitly disabled
        if isinstance(auth, Sentinel):
            # Nothing is set on the endpoint and the controller levels,
            # settings is the last place we look at.
            # `SyncOrAsyncAuth` is resolved to the actual instance here.
            settings_auth: Sequence[
                SyncAuth | AsyncAuth | SyncOrAsyncAuth[Any, Any]
            ] = resolve_setting(Settings.auth)
            resolved_auth = [
                setting_auth.resolve(is_async=base_type is AsyncAuth)
                if isinstance(setting_auth, SyncOrAsyncAuth)
                else setting_auth
                for setting_auth in settings_auth
            ]
        else:
            resolved_auth = list(auth)
            # `SyncOrAsyncAuth` is settings-only,
            # reject controller / endpoint usage:
            if any(
                isinstance(candidate_auth, SyncOrAsyncAuth)  # pyright: ignore[reportUnnecessaryIsInstance]
                for candidate_auth in resolved_auth
            ):
                raise EndpointMetadataError(
                    'SyncOrAsyncAuth can only be used in settings, '
                    'not at controller or endpoint level '
                    f'for {self.endpoint_name=}',
                )
        # Validate that auth matches the sync / async endpoints:
        if not all(
            isinstance(auth_instance, base_type)  # pyright: ignore[reportUnnecessaryIsInstance]
            for auth_instance in resolved_auth
        ):
            raise EndpointMetadataError(
                f'All auth instances must be subtypes of {base_type!r} '
                f'for {self.endpoint_name=}',
            )
        # Empty auth list means that no auth is configured
        # and it is just `None`.
        return resolved_auth or None

    def _build_throttling(  # noqa: WPS210, WPS231
        self,
    ) -> tuple[
        list[SyncThrottle | AsyncThrottle] | None,
        list[SyncThrottle | AsyncThrottle] | None,
        bool | None,
    ]:
        base_type = (
            AsyncThrottle
            if inspect.iscoroutinefunction(self.func)
            else SyncThrottle
        )
        allow_cache = self._build_throttling_allow_unsafe_cache()
        throttling = first_defined(
            self.payload.throttling if self.payload else EMPTY,
            self.controller_cls.throttling,
        )
        if throttling is None:
            return (None, None, allow_cache)  # explicitly disabled
        if isinstance(throttling, Sentinel):
            # Nothing is set on the endpoint and the controller levels,
            # settings is the last place we look at.
            # `SyncOrAsyncThrottle` is resolved to the actual instance here.
            settings_throttling: Sequence[
                SyncThrottle | AsyncThrottle | SyncOrAsyncThrottle[Any, Any]
            ] = resolve_setting(Settings.throttling)
            resolved_throttling = [
                setting_throttle.resolve(is_async=base_type is AsyncThrottle)
                if isinstance(setting_throttle, SyncOrAsyncThrottle)
                else setting_throttle
                for setting_throttle in settings_throttling
            ]
        else:
            resolved_throttling = list(throttling)
            # `SyncOrAsyncThrottle` is settings-only,
            # reject controller / endpoint usage:
            if any(
                isinstance(throttle, SyncOrAsyncThrottle)  # pyright: ignore[reportUnnecessaryIsInstance]
                for throttle in resolved_throttling
            ):
                raise EndpointMetadataError(
                    'SyncOrAsyncThrottle can only be used in settings, '
                    'not at controller or endpoint level '
                    f'for {self.endpoint_name=}',
                )
        # Validate that throttling matches the sync / async endpoints:
        if not all(
            isinstance(throttling_instance, base_type)  # pyright: ignore[reportUnnecessaryIsInstance]
            for throttling_instance in resolved_throttling
        ):
            raise EndpointMetadataError(
                f'All throttling instances must be subtypes of {base_type!r} '
                f'for {self.endpoint_name=}',
            )
        self._validate_throttling(resolved_throttling, allow_cache=allow_cache)
        # Empty throttling list means that no throttling is configured
        # and it is just `None`.
        if not resolved_throttling:
            return (None, None, allow_cache)
        return (
            (
                [
                    throttle
                    for throttle in resolved_throttling
                    if throttle.cache_key.runs_before_auth
                ]
                or None
            ),
            (
                [
                    throttle
                    for throttle in resolved_throttling
                    if not throttle.cache_key.runs_before_auth
                ]
                or None
            ),
            allow_cache,
        )

    def _build_throttling_allow_unsafe_cache(self) -> bool | None:
        if self.payload and not isinstance(
            self.payload.throttling_allow_unsafe_cache,
            Sentinel,
        ):
            return self.payload.throttling_allow_unsafe_cache
        if not isinstance(
            self.controller_cls.throttling_allow_unsafe_cache,
            Sentinel,
        ):
            return self.controller_cls.throttling_allow_unsafe_cache
        return resolve_setting(  # type: ignore[no-any-return]
            Settings.throttling_allow_unsafe_cache,
        )

    def _validate_throttling(
        self,
        throttling: Sequence[SyncThrottle | AsyncThrottle],
        *,
        allow_cache: bool | None,
    ) -> None:
        for throttle in throttling:
            if (
                allow_cache is None
                or not isinstance(
                    throttle._backend,  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    (SyncDjangoCache, AsyncDjangoCache),
                )
                or not isinstance(
                    throttle._backend._cache,  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                    (locmem.LocMemCache, dummy.DummyCache),
                )
            ):
                continue

            cache = throttle._backend._cache  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            backend = type(cache).__qualname__
            msg = (
                f'Throttling is using {backend!r} cache backend '
                f'in {self.endpoint_name!r} which is not safe for production: '
                'counters are NOT shared between processes/instances. '
                'Use Redis or Memcached backends instead.'
            )
            if allow_cache:
                warnings.warn(
                    msg,
                    category=UnsafeCacheBackendWarning,
                    stacklevel=1,
                )
            else:
                raise EndpointMetadataError(msg)

    def _build_validate_responses(self) -> bool:
        settings_value: bool | Sentinel = resolve_setting(
            Settings.validate_responses,
        )
        validate_responses = first_set(
            self.payload.validate_responses if self.payload else EMPTY,
            self.controller_cls.validate_responses,
            settings_value,
        )
        # Settings is the last level, validation is enabled by default:
        if isinstance(validate_responses, Sentinel):
            return True
        return validate_responses

    def _build_validate_events(self) -> bool:
        settings_value: bool | Sentinel = resolve_setting(
            Settings.validate_events,
        )
        validate_events = first_set(
            self.payload.validate_events if self.payload else EMPTY,
            self.controller_cls.validate_events,
            settings_value,
        )
        if isinstance(validate_events, Sentinel):
            return self._build_validate_responses()
        return validate_events

    def _build_ignore_from_spec(self) -> bool:
        ignore_from_spec = first_set(
            self.payload.ignore_from_spec if self.payload else EMPTY,
            self.controller_cls.ignore_from_spec,
        )
        return not isinstance(ignore_from_spec, Sentinel) and ignore_from_spec

    def _build_tags(
        self,
        payload_tags: Sequence[str] | Sentinel | None,
    ) -> list[str] | Sentinel | None:
        # Router-level tags are resolved later during the schema generation,
        # that's why `EMPTY` is preserved here.
        tags = first_defined(payload_tags, self.controller_cls.tags)
        if tags is None or isinstance(tags, Sentinel):
            return tags
        return list(tags)

    def _build_error_handler(
        self,
    ) -> 'SyncErrorHandler | AsyncErrorHandler | None':
        if self.payload is None or isinstance(
            self.payload.error_handler,
            Sentinel,
        ):
            return None
        if inspect.iscoroutinefunction(self.func):
            if not inspect.iscoroutinefunction(self.payload.error_handler):
                raise EndpointMetadataError(
                    'Cannot pass sync `error_handler` '
                    f'to async {self.endpoint_name!r}',
                )
        elif inspect.iscoroutinefunction(self.payload.error_handler):
            raise EndpointMetadataError(
                'Cannot pass async `error_handler` '
                f'to sync {self.endpoint_name!r}',
            )
        return self.payload.error_handler

    def _build_no_validate_http_spec(self) -> frozenset[HttpSpec]:
        return self._build_optional_set(
            self.payload.no_validate_http_spec if self.payload else EMPTY,
            self.controller_cls.no_validate_http_spec,
            resolve_setting(Settings.no_validate_http_spec),
        )

    def _build_semantic_responses(self) -> bool:
        settings_value: bool | Sentinel = resolve_setting(
            Settings.semantic_responses,
        )
        semantic_responses = first_set(
            self.payload.semantic_responses if self.payload else EMPTY,
            self.controller_cls.semantic_responses,
            settings_value,
        )
        # Settings is the last level, semantic responses are on by default:
        if isinstance(semantic_responses, Sentinel):
            return True
        return semantic_responses

    def _build_exclude_validate_responses(self) -> frozenset[HTTPStatus]:
        return self._build_optional_set(
            self.payload.exclude_validate_responses if self.payload else EMPTY,
            self.controller_cls.exclude_validate_responses,
            resolve_setting(Settings.exclude_validate_responses),
        )

    def _build_exclude_semantic_responses(self) -> frozenset[HTTPStatus]:
        return self._build_optional_set(
            self.payload.exclude_semantic_responses if self.payload else EMPTY,
            self.controller_cls.exclude_semantic_responses,
            resolve_setting(Settings.exclude_semantic_responses),
        )

    def _build_optional_set(
        self,
        *layers: Set[_ItemT] | Sentinel | None,
    ) -> frozenset[_ItemT]:
        resolved = first_defined(*layers)
        if resolved is None or isinstance(resolved, Sentinel):
            return frozenset()
        return frozenset(resolved)

    def _build_description(self) -> tuple[str | None, str | None]:
        """
        Resolve summary and description for an endpoint.

        Uses the very same rules as a controller does for its path item:
        each one is parsed from ``func.__doc__`` on its own,
        unless ``@modify`` or ``@validate`` sets it explicitly.
        """
        return resolve_summary_and_description(
            self.func.__doc__,
            EMPTY if self.payload is None else self.payload.summary,
            EMPTY if self.payload is None else self.payload.description,
        )

    def _validate_new_http_parts(
        self,
        payload: ModifyEndpointPayload,
    ) -> None:
        headers = empty_to_none(payload.headers)
        if headers is not None and any(
            isinstance(header, HeaderSpec) and not header.skip_validation
            for header in headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {self.endpoint_name!r} returns raw data, '
                f'it is not possible to use `HeaderSpec` '
                'because there are no existing headers to describe. Use '
                '`NewHeader` to add new headers to the response. '
                'Or add `skip_validation=True` to `HeaderSpec`',
            )
        cookies = empty_to_none(payload.cookies)
        if cookies is not None and any(
            isinstance(cookie, CookieSpec) and not cookie.skip_validation
            for cookie in cookies.values()
        ):
            raise EndpointMetadataError(
                f'Since {self.endpoint_name!r} returns raw data, '
                f'it is not possible to use `CookieSpec` '
                'because there are no existing cookies to describe. Use '
                '`NewCookie` to add new cookies to the response. '
                'Or add `skip_validation=True` to `CookieSpec`',
            )

    def _validate_return_annotation(
        self,
        return_annotation: Any,
    ) -> None:
        if is_safe_subclass(return_annotation, HttpResponseBase):
            if isinstance(self.payload, ModifyEndpointPayload):
                raise EndpointMetadataError(
                    f'{self.endpoint_name!r} returns HttpResponseBase '
                    'it cannot be used with `@modify`. '
                    'Maybe you meant `@validate`?',
                )
            # We can't reach this point with `None`, it is processed before.
            assert isinstance(self.payload, ValidateEndpointPayload)  # noqa: S101
            if not _build_responses(
                self.payload,
                controller_cls=self.controller_cls,
            ):
                raise EndpointMetadataError(
                    f'{self.endpoint_name!r} returns HttpResponse '
                    'and has no configured responses, '
                    'it requires `@validate` decorator with '
                    'at least one configured `ResponseSpec`',
                )

            # There are some configured errors,
            # we will check them in runtime if they are correct or not.
            return

        if isinstance(self.payload, ValidateEndpointPayload):
            raise EndpointMetadataError(
                f'{self.endpoint_name!r} returns raw data, '
                'it requires `@modify` decorator instead of `@validate`',
            )


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadataValidator:  # noqa: WPS214
    """
    Builds responses for the endpoint metadata.

    Runs semantic validation.

    Metadata will be considered ready after running this process.
    """

    response_list_validator_cls: ClassVar[type[_ResponseListValidator]] = (
        _ResponseListValidator
    )

    metadata: EndpointMetadata

    def __call__(
        self,
        func: Callable[..., Any],
        payload: Payload,
        *,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """Collect and validate all responses."""
        responses = self._resolve_all_responses(
            payload,
            controller_cls=controller_cls,
        )
        # It is kinda bad to mutate a frozen object,
        # but metadata is not finished just yet. So, it is technically ok.
        # Collecting responses from all of the providers is kinda hard.
        object.__setattr__(
            self.metadata,
            'responses',
            self.response_list_validator_cls(
                metadata=self.metadata,
            )(responses),
        )
        # After that we can do some other validation:
        self._validate_request_http_spec()
        self._validate_components(controller_cls)
        self._validate_parsers(controller_cls)
        self._validate_renderers(controller_cls)

    def _resolve_all_responses(
        self,
        payload: Payload,
        *,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[ResponseSpec]:
        all_responses = self._limit_streaming_responses([
            self._resolve_response_type(
                response,
                controller_cls=controller_cls,
            )
            for response in _build_responses(
                payload=payload,
                controller_cls=controller_cls,
                modification=self.metadata.modification,
            )
        ])
        existing_responses = {
            response.status_code: response for response in all_responses
        }
        all_responses.extend(
            self.metadata.collect_response_specs(
                controller_cls,
                existing_responses,
            ),
        )
        return all_responses

    def _resolve_response_type(
        self,
        response: ResponseSpec,
        *,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> ResponseSpec:
        # This method resolves `_ModelT` type var in reusable controllers
        # to its real value.
        # In case it is not a type var, just return whatever it is.
        if isinstance(response.return_type, TypeVar):
            return dataclasses.replace(
                response,
                return_type=infer_annotation(
                    response.return_type,
                    controller_cls,
                ),
            )
        return response

    def _limit_streaming_responses(
        self,
        responses: list[ResponseSpec],
    ) -> list[ResponseSpec]:
        streaming_renderers = {
            renderer.content_type
            for renderer in self.metadata.renderers.values()
            if renderer.streaming
        }

        limited: list[ResponseSpec] = []
        for response in responses:
            if response.streaming:
                limited.append(
                    dataclasses.replace(
                        response,
                        limit_to_content_types=streaming_renderers,
                    ),
                )
            else:
                limited.append(response)
        return limited

    def _validate_components(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        for component, _model, _metadata in self.metadata.component_parsers:
            component.validate(controller_cls, self.metadata)

    def _validate_parsers(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        for parser in self.metadata.parsers.values():
            parser.validate(controller_cls, self.metadata)

    def _validate_renderers(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        for renderer in self.metadata.renderers.values():
            renderer.validate(controller_cls, self.metadata)

    def _validate_request_http_spec(self) -> None:
        """Validate HTTP spec rules for request."""
        if (
            HttpSpec.empty_request_body
            not in self.metadata.no_validate_http_spec
        ):
            self._check_empty_request_body()

    def _check_empty_request_body(self) -> None:
        """Validate that methods without body don't use Body component.

        According to HTTP spec, methods like GET, HEAD, DELETE, CONNECT, TRACE
        should not have a request body. If a controller uses Body component
        with these methods, an EndpointMetadataError will be raised.
        """
        method = stringify(self.metadata.method).upper()
        if method not in _HTTP_METHODS_WITHOUT_BODY:
            return

        has_body = any(
            isinstance(component[0], BodyComponent)
            for component in self.metadata.component_parsers
        )
        if has_body:
            endpoint_name = self.metadata.endpoint_name
            raise EndpointMetadataError(
                f'HTTP method {method!r} cannot have a request body, '
                f'but endpoint {endpoint_name!r} uses Body component. '
                f'Either remove Body component or use a different HTTP method '
                f'like POST, PUT, or PATCH.',
            )


def _build_responses(
    payload: Payload,
    *,
    controller_cls: type['Controller[BaseSerializer]'],
    modification: ResponseModification | None = None,
) -> list[ResponseSpec]:
    responses = first_defined(
        payload.responses if payload else EMPTY,
        controller_cls.responses,
        resolve_setting(Settings.responses),
    )
    return [
        *(
            []
            if responses is None or isinstance(responses, Sentinel)
            else responses
        ),
        *([] if modification is None else [modification.to_spec()]),
    ]


def _resolve_return_annotation(
    type_annotations: dict[str, Any],
    controller_cls: type['Controller[BaseSerializer]'],
    endpoint_func: Callable[..., Any],
) -> Any:
    return_annotation = type_annotations.get('return', EMPTY)
    if return_annotation is EMPTY:
        raise UnsolvableAnnotationsError(
            f'Function {endpoint_func!r} is missing return type annotation',
        )
    return infer_annotation(return_annotation, controller_cls)


def validate_method_name(
    func_name: str,
    *,
    allowed_http_methods: Set[str],
) -> str:
    """Validates that a function has correct HTTP method name."""
    if func_name != func_name.lower():
        raise EndpointMetadataError(
            f'{func_name} is not a valid HTTP method name',
        )
    if func_name == 'meta':
        return 'options'
    if func_name in allowed_http_methods:
        return func_name

    try:
        return HTTPMethod(func_name.upper()).value.lower()
    except ValueError:
        raise EndpointMetadataError(
            f'{func_name} is not a valid HTTP method name',
        ) from None
