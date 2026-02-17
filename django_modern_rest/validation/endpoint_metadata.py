import dataclasses
import inspect
from collections.abc import Callable, Sequence, Set
from http import HTTPMethod, HTTPStatus
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    assert_never,
)

from django.contrib.admindocs.utils import parse_docstring
from django.http import HttpResponseBase

from django_modern_rest.components import Body
from django_modern_rest.cookies import CookieSpec, NewCookie
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.headers import HeaderSpec, NewHeader
from django_modern_rest.metadata import (
    EndpointMetadata,
    ResponseModification,
    ResponseSpec,
)
from django_modern_rest.parsers import Parser
from django_modern_rest.renderers import Renderer
from django_modern_rest.response import infer_status_code
from django_modern_rest.security.base import AsyncAuth, SyncAuth
from django_modern_rest.serializer import BaseSerializer
from django_modern_rest.settings import HttpSpec, Settings, resolve_setting
from django_modern_rest.types import (
    infer_annotation,
    is_safe_subclass,
    parse_return_annotation,
)
from django_modern_rest.validation.payload import (
    ModifyEndpointPayload,
    Payload,
    ValidateEndpointPayload,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller
    from django_modern_rest.errors import AsyncErrorHandler, SyncErrorHandler

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


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ResponseListValidator:  # noqa: WPS214
    """Validates responses metadata."""

    metadata: EndpointMetadata
    endpoint: str

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
        # Now, check if we have any conflicts in responses.
        # For example: same status code, mismatching metadata.
        unique: dict[HTTPStatus, ResponseSpec] = {}
        for response in responses:
            existing_response = unique.get(response.status_code)
            if existing_response is not None and existing_response != response:
                raise EndpointMetadataError(
                    f'Endpoint {self.endpoint!r} has multiple responses '
                    f'for {response.status_code=}, but with different '
                    f'metadata: {response} and {existing_response}',
                )
            unique.setdefault(response.status_code, response)

    def _validate_header_descriptions(  # noqa: WPS231
        self,
        responses: list[ResponseSpec],
    ) -> None:
        for response in responses:
            if response.headers is None:
                continue
            for header_name, header in response.headers.items():
                if header_name.lower() == 'set-cookie':
                    raise EndpointMetadataError(
                        f'Cannot use "Set-Cookie" header in {response}, use '
                        f'`cookies=` parameter instead in {self.endpoint!r}',
                    )
                if isinstance(header, NewHeader):  # type: ignore[unreachable]
                    raise EndpointMetadataError(
                        f'Cannot use `NewHeader` in {response} , use '
                        f'`HeaderSpec` instead in {self.endpoint!r}',
                    )

    def _validate_cookie_descriptions(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        for response in responses:
            if response.cookies is None:
                continue
            if any(
                isinstance(cookie, NewCookie)  # pyright: ignore[reportUnnecessaryIsInstance]
                for cookie in response.cookies.values()
            ):
                raise EndpointMetadataError(
                    f'Cannot use `NewCookie` in {response} , '
                    f'use `CookieSpec` instead in {self.endpoint!r}',
                )

    def _validate_http_spec(
        self,
        responses: list[ResponseSpec],
    ) -> None:
        """Validate that we don't violate HTTP spec."""
        if (
            HttpSpec.empty_response_body
            not in self.metadata.no_validate_http_spec
        ):
            self._check_empty_response_body(
                responses,
                endpoint=self.endpoint,
            )
        # TODO: add more checks

    def _check_empty_response_body(
        self,
        responses: list[ResponseSpec],
        *,
        endpoint: str,
    ) -> None:
        # For status codes < 100 or 204, 304 statuses,
        # no response body is allowed.
        # If you specify a return annotation other than None,
        # an EndpointMetadataError will be raised.
        for response in responses:
            if not is_safe_subclass(response.return_type, NoneType) and (
                response.status_code < HTTPStatus.CONTINUE
                or response.status_code
                in {HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED}
            ):
                raise EndpointMetadataError(
                    f'Can only return `None` not {response.return_type} '
                    f'from an endpoint {endpoint!r} '
                    f'with status code {response.status_code}',
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
    blueprint_cls: type['Blueprint[BaseSerializer]'] | None
    controller_cls: type['Controller[BaseSerializer]']
    func: Callable[..., Any]

    def __call__(self) -> EndpointMetadata:
        """Do the validation."""
        return_annotation = infer_annotation(
            parse_return_annotation(self.func),
            self.blueprint_cls or self.controller_cls,
        )
        if self.payload is None and is_safe_subclass(
            return_annotation,
            HttpResponseBase,
        ):
            object.__setattr__(
                self,
                'payload',
                ValidateEndpointPayload(responses=[]),
            )
        allowed_http_methods: frozenset[str] = frozenset((
            *(
                self.blueprint_cls.allowed_http_methods
                if self.blueprint_cls
                else set()
            ),
            *self.controller_cls.allowed_http_methods,
        ))
        method = validate_method_name(
            self.func.__name__,
            allowed_http_methods=allowed_http_methods,
        )
        self.func.__name__ = method  # we can change it :)
        endpoint = str(self.func)

        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
        )

        if isinstance(self.payload, ValidateEndpointPayload):
            return self._from_validate(
                self.payload,
                method,
                endpoint=endpoint,
                allowed_http_methods=allowed_http_methods,
            )
        if isinstance(self.payload, ModifyEndpointPayload):
            return self._from_modify(
                self.payload,
                method,
                return_annotation,
                endpoint=endpoint,
                allowed_http_methods=allowed_http_methods,
            )
        if self.payload is None:
            return self._from_raw_data(
                method,
                return_annotation,
                endpoint=endpoint,
                allowed_http_methods=allowed_http_methods,
            )
        assert_never(self.payload)

    def _from_validate(  # noqa: WPS211
        self,
        payload: ValidateEndpointPayload,
        method: str,
        *,
        endpoint: str,
        allowed_http_methods: frozenset[str],
    ) -> EndpointMetadata:
        summary, description = self._build_description()
        return payload.metadata_cls(
            responses={},
            method=method,
            validate_responses=self._build_validate_responses(),
            modification=None,
            error_handler=self._build_error_handler(endpoint=endpoint),
            component_parsers=(
                (self.blueprint_cls or self.controller_cls)._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            ),
            parsers=self._build_parsers(endpoint=endpoint),
            renderers=self._build_renderers(endpoint=endpoint),
            auth=self._build_auth(endpoint=endpoint),
            no_validate_http_spec=self._build_no_validate_http_spec(),
            allowed_http_methods=allowed_http_methods,
            summary=summary,
            description=description,
            tags=payload.tags,
            operation_id=payload.operation_id,
            deprecated=payload.deprecated,
            external_docs=payload.external_docs,
            callbacks=payload.callbacks,
            servers=payload.servers,
        )

    def _from_modify(
        self,
        payload: ModifyEndpointPayload,
        method: str,
        return_annotation: Any,
        *,
        endpoint: str,
        allowed_http_methods: frozenset[str],
    ) -> EndpointMetadata:
        self._validate_new_http_parts(payload, endpoint=endpoint)
        modification = ResponseModification(
            return_type=return_annotation,
            headers=payload.headers,
            cookies=payload.cookies,
            status_code=(
                infer_status_code(method)
                if payload.status_code is None
                else payload.status_code
            ),
        )
        summary, description = self._build_description()
        return payload.metadata_cls(
            responses={},
            validate_responses=self._build_validate_responses(),
            method=method,
            modification=modification,
            error_handler=self._build_error_handler(endpoint=endpoint),
            component_parsers=(
                (self.blueprint_cls or self.controller_cls)._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            ),
            parsers=self._build_parsers(endpoint=endpoint),
            renderers=self._build_renderers(endpoint=endpoint),
            auth=self._build_auth(endpoint=endpoint),
            no_validate_http_spec=self._build_no_validate_http_spec(),
            allowed_http_methods=allowed_http_methods,
            summary=summary,
            description=description,
            tags=payload.tags,
            operation_id=payload.operation_id,
            deprecated=payload.deprecated,
            external_docs=payload.external_docs,
            callbacks=payload.callbacks,
            servers=payload.servers,
        )

    def _from_raw_data(
        self,
        method: str,
        return_annotation: Any,
        *,
        endpoint: str,
        allowed_http_methods: frozenset[str],
    ) -> EndpointMetadata:
        status_code = infer_status_code(method)
        modification = ResponseModification(
            return_type=return_annotation,
            status_code=status_code,
            headers=None,
            cookies=None,
        )
        summary, description = self._build_description()
        return EndpointMetadata(
            responses={},
            validate_responses=self._build_validate_responses(),
            method=method,
            modification=modification,
            error_handler=None,
            component_parsers=(
                (self.blueprint_cls or self.controller_cls)._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            ),
            parsers=self._build_parsers(endpoint=endpoint),
            renderers=self._build_renderers(endpoint=endpoint),
            auth=self._build_auth(endpoint=endpoint),
            no_validate_http_spec=self._build_no_validate_http_spec(),
            allowed_http_methods=allowed_http_methods,
            summary=summary,
            description=description,
        )

    def _build_parsers(self, *, endpoint: str) -> dict[str, Parser]:
        if self.payload and self.payload.parsers:
            return {typ.content_type: typ for typ in self.payload.parsers}
        if self.blueprint_cls and self.blueprint_cls.parsers:
            return {typ.content_type: typ for typ in self.blueprint_cls.parsers}
        if self.controller_cls.parsers:
            return {
                typ.content_type: typ for typ in self.controller_cls.parsers
            }
        settings_types = resolve_setting(Settings.parsers)
        if not settings_types:
            # This is the last place we look at, it must be present:
            raise EndpointMetadataError(
                f'{endpoint!r} must have at least one parser '
                'configured in settings',
            )
        return {typ.content_type: typ for typ in settings_types}

    def _build_renderers(self, *, endpoint: str) -> dict[str, Renderer]:
        if self.payload and self.payload.renderers:
            return {typ.content_type: typ for typ in self.payload.renderers}
        if self.blueprint_cls and self.blueprint_cls.renderers:
            return {
                typ.content_type: typ for typ in self.blueprint_cls.renderers
            }
        if self.controller_cls.renderers:
            return {
                typ.content_type: typ for typ in self.controller_cls.renderers
            }
        settings_types = resolve_setting(Settings.renderers)
        if not settings_types:
            # This is the last place we look at, it must be present:
            raise EndpointMetadataError(
                f'{endpoint!r} must have at least one renderer '
                'configured in settings',
            )
        return {typ.content_type: typ for typ in settings_types}

    def _build_auth(  # noqa: WPS231
        self,
        *,
        endpoint: str,
    ) -> list[SyncAuth | AsyncAuth] | None:
        payload_auth = () if self.payload is None else (self.payload.auth or ())
        blueprint_auth = (
            ()
            if self.blueprint_cls is None
            else (self.blueprint_cls.auth or ())
        )
        settings_auth: list[SyncAuth | AsyncAuth] = resolve_setting(
            Settings.auth,
        )
        if not isinstance(settings_auth, Sequence):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise EndpointMetadataError(
                'Settings.auth must be a list of auth instances. '
                f'Got: {settings_auth!r}',
            )

        auth = [
            *payload_auth,  # pyrefly: ignore[not-iterable]
            *blueprint_auth,  # pyrefly: ignore[not-iterable]
            *(self.controller_cls.auth or ()),  # pyrefly: ignore[not-iterable]
            # TODO: maybe we should wrap auth handlers in global settings
            # in `sync_to_async` and `async_to_sync`?
            *(settings_auth or ()),  # pyrefly: ignore[not-iterable]
        ]
        # Validate that auth matches the sync / async endpoints:
        base_type = (
            AsyncAuth if inspect.iscoroutinefunction(self.func) else SyncAuth
        )
        if not all(
            isinstance(auth_instance, base_type)  # pyright: ignore[reportUnnecessaryIsInstance]
            for auth_instance in auth
        ):
            raise EndpointMetadataError(
                f'All auth instances must be subtypes of {base_type!r} '
                f'for {endpoint=}',
            )
        # We are doing this as late as possible to still
        # have the full validation logic even if some value is None.
        if (
            (self.payload and self.payload.auth is None)  # noqa: WPS222
            or (self.blueprint_cls and self.blueprint_cls.auth is None)
            or self.controller_cls.auth is None
            # Empty auth list means that no auth is configured
            # and it is just None.
            or not auth
        ):
            return None
        return auth

    def _build_validate_responses(self) -> bool:
        if self.payload and self.payload.validate_responses is not None:
            return self.payload.validate_responses
        if (
            self.blueprint_cls
            and self.blueprint_cls.validate_responses is not None
        ):
            return self.blueprint_cls.validate_responses
        if self.controller_cls.validate_responses is not None:
            return self.controller_cls.validate_responses
        return resolve_setting(  # type: ignore[no-any-return]
            Settings.validate_responses,
        )

    def _build_error_handler(
        self,
        *,
        endpoint: str,
    ) -> 'SyncErrorHandler | AsyncErrorHandler | None':
        if self.payload is None or self.payload.error_handler is None:
            return None
        if inspect.iscoroutinefunction(self.func):
            if not inspect.iscoroutinefunction(self.payload.error_handler):
                raise EndpointMetadataError(
                    f'Cannot pass sync `error_handler` to async {endpoint}',
                )
        elif inspect.iscoroutinefunction(self.payload.error_handler):
            raise EndpointMetadataError(
                f'Cannot pass async `error_handler` to sync {endpoint}',
            )
        return self.payload.error_handler

    def _build_no_validate_http_spec(self) -> frozenset[HttpSpec]:
        payload_spec: Set[HttpSpec] = (
            (self.payload.no_validate_http_spec or set())
            if self.payload
            else set()
        )
        blueprint_spec: Set[HttpSpec] = (
            self.blueprint_cls.no_validate_http_spec
            if self.blueprint_cls
            else set()
        )
        return frozenset((
            *payload_spec,
            *blueprint_spec,
            *self.controller_cls.no_validate_http_spec,
            *resolve_setting(Settings.no_validate_http_spec),
        ))

    def _build_description(self) -> tuple[str | None, str | None]:
        """
        Resolve summary and description for an endpoint.

        Follows the priority:

        1. If payload is provided and has non-None , returns those.
        2. If func has no docstring,
           returns payload values (or None if no payload).
        3. Otherwise extracts values from ``func.__doc__``
           via django's ``parse_docstring()`` helper

        All empty strings are converted to ``None``.
        """
        if self.payload is not None:
            if (
                self.payload.summary is not None
                or self.payload.description is not None
            ):
                return self.payload.summary, self.payload.description

            if self.func.__doc__ is None:
                return self.payload.summary, self.payload.description

        summary: str | None
        description: str | None

        summary, description, _ = parse_docstring(self.func.__doc__ or '')

        if not summary:
            summary = None

        if not description:
            description = None

        return summary, description

    def _validate_new_http_parts(
        self,
        payload: ModifyEndpointPayload,
        *,
        endpoint: str,
    ) -> None:
        if payload.headers is not None and any(
            isinstance(header, HeaderSpec) and not header.schema_only
            for header in payload.headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns raw data, '
                f'it is not possible to use `HeaderSpec` '
                'because there are no existing headers to describe. Use '
                '`NewHeader` to add new headers to the response. '
                'Or add `schema_only=True` to `HeaderSpec`',
            )
        if payload.cookies is not None and any(
            isinstance(cookie, CookieSpec) and not cookie.schema_only
            for cookie in payload.cookies.values()
        ):
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns raw data, '
                f'it is not possible to use `CookieSpec` '
                'because there are no existing cookies to describe. Use '
                '`NewCookie` to add new cookies to the response. '
                'Or add `schema_only=True` to `CookieSpec`',
            )

    def _validate_return_annotation(
        self,
        return_annotation: Any,
        *,
        endpoint: str,
    ) -> None:
        if is_safe_subclass(return_annotation, HttpResponseBase):
            if isinstance(self.payload, ModifyEndpointPayload):
                raise EndpointMetadataError(
                    f'{endpoint!r} returns HttpResponseBase '
                    'it cannot be used with `@modify`. '
                    'Maybe you meant `@validate`?',
                )
            # We can't reach this point with `None`, it is processed before.
            assert isinstance(self.payload, ValidateEndpointPayload)  # noqa: S101
            if not _build_responses(
                self.payload,
                blueprint_cls=self.blueprint_cls,
                controller_cls=self.controller_cls,
            ):
                raise EndpointMetadataError(
                    f'{endpoint!r} returns HttpResponse '
                    'and has no configured responses, '
                    'it requires `@validate` decorator with '
                    'at least one configured `ResponseSpec`',
                )

            # There are some configured errors,
            # we will check them in runtime if they are correct or not.
            return

        if isinstance(self.payload, ValidateEndpointPayload):
            raise EndpointMetadataError(
                f'{endpoint!r} returns raw data, '
                'it requires `@modify` decorator instead of `@validate`',
            )


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadataValidator:
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """Collect and validate all responses."""
        endpoint = str(func)
        responses = self._resolve_all_responses(
            payload,
            blueprint_cls=blueprint_cls,
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
                endpoint=endpoint,
            )(responses),
        )
        # After that we can do some other validation:
        self._validate_request_http_spec(endpoint=endpoint)
        self._validate_components()

    def _resolve_all_responses(
        self,
        payload: Payload,
        *,
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[ResponseSpec]:
        all_responses = _build_responses(
            payload=payload,
            controller_cls=controller_cls,
            blueprint_cls=blueprint_cls,
            modification=self.metadata.modification,
        )
        existing_responses = {
            response.status_code: response for response in all_responses
        }
        for provider in self.metadata.response_spec_providers():
            responses = provider.provide_response_specs(
                self.metadata,
                controller_cls,
                existing_responses,
            )
            all_responses.extend(responses)
            existing_responses.update({
                response.status_code: response for response in responses
            })
        return all_responses

    def _validate_components(self) -> None:
        for component, _model in self.metadata.component_parsers:
            component.validate(self.metadata)

    def _validate_request_http_spec(
        self,
        *,
        endpoint: str,
    ) -> None:
        """Validate HTTP spec rules for request."""
        if (
            HttpSpec.empty_request_body
            not in self.metadata.no_validate_http_spec
        ):
            self._check_empty_request_body(endpoint=endpoint)

    def _check_empty_request_body(
        self,
        *,
        endpoint: str,
    ) -> None:
        """Validate that methods without body don't use Body component.

        According to HTTP spec, methods like GET, HEAD, DELETE, CONNECT, TRACE
        should not have a request body. If a controller uses Body component
        with these methods, an EndpointMetadataError will be raised.
        """
        method = str(self.metadata.method).upper()
        if method not in _HTTP_METHODS_WITHOUT_BODY:
            return

        has_body = any(
            is_safe_subclass(component_cls, Body)
            for component_cls, _ in self.metadata.component_parsers
        )
        if has_body:
            raise EndpointMetadataError(
                f'HTTP method {method!r} cannot have a request body, '
                f'but endpoint {endpoint!r} uses Body component. '
                f'Either remove Body component or use a different HTTP method '
                f'like POST, PUT, or PATCH.',
            )


def _build_responses(
    payload: Payload,
    *,
    blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
    controller_cls: type['Controller[BaseSerializer]'],
    modification: ResponseModification | None = None,
) -> list[ResponseSpec]:
    return [
        *resolve_setting(Settings.responses),
        *controller_cls.responses,
        *(blueprint_cls.responses if blueprint_cls else []),
        *((payload.responses or []) if payload else []),
        *([] if modification is None else [modification.to_spec()]),
    ]


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
