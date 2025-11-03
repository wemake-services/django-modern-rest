import dataclasses
import inspect
from collections.abc import Callable, Mapping, Set
from functools import lru_cache
from http import HTTPMethod, HTTPStatus
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NewType,
    TypeAlias,
    TypeVar,
    assert_never,
    cast,
    final,
    get_args,
)

from django.http import HttpResponse
from typing_extensions import override

from django_modern_rest.components import ComponentParser
from django_modern_rest.cookies import NewCookie
from django_modern_rest.errors import AsyncErrorHandlerT, SyncErrorHandlerT
from django_modern_rest.exceptions import (
    EndpointMetadataError,
    ResponseSerializationError,
)
from django_modern_rest.headers import (
    HeaderSpec,
    NewHeader,
    build_headers,
)
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.response import (
    ResponseModification,
    ResponseSpec,
    infer_status_code,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    MAX_CACHE_SIZE,
    Settings,
    resolve_setting,
)
from django_modern_rest.types import (
    infer_bases,
    is_safe_subclass,
    parse_return_annotation,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.openapi.objects import (
        Callback,
        ExternalDocumentation,
        Reference,
        SecurityRequirement,
        Server,
    )

_ResponseT = TypeVar('_ResponseT', bound=HttpResponse)


@dataclasses.dataclass(frozen=True, slots=True)
class ResponseValidator:
    """
    Response validator.

    Can validate responses that return raw data as well as real ``HttpResponse``
    that are returned from endpoints.
    """

    # Public API:
    metadata: 'EndpointMetadata'
    serializer: type[BaseSerializer]
    strict_validation: ClassVar[bool] = True

    def validate_response(
        self,
        controller: 'Controller[BaseSerializer]',
        response: _ResponseT,
    ) -> _ResponseT:
        """Validate ``.content`` of existing ``HttpResponse`` object."""
        if not _is_validation_enabled(
            controller,
            metadata_validate_responses=self.metadata.validate_responses,
        ):
            return response
        schema = self._get_response_schema(response.status_code)
        self._validate_body(response.content, schema, response=response)
        self._validate_response_headers(response, schema)
        self._validate_response_cookies(response, schema)
        return response

    def validate_modification(
        self,
        controller: 'Controller[BaseSerializer]',
        structured: Any,
    ) -> '_ValidationContext':
        """Validate *structured* data before dumping it to json."""
        if self.metadata.modification is None:
            method = self.metadata.method
            raise ResponseSerializationError(
                f'{controller} in {method} returned '
                f'raw data of type {type(structured)} '
                'without associated `@modify` usage.',
            )

        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.modification.status_code,
            headers=build_headers(
                self.metadata.modification,
                self.serializer,
            ),
            cookies=self.metadata.modification.cookies,
        )
        if not _is_validation_enabled(
            controller,
            metadata_validate_responses=self.metadata.validate_responses,
        ):
            return all_response_data
        schema = self._get_response_schema(all_response_data.status_code)
        self._validate_body(structured, schema)
        return all_response_data

    def _get_response_schema(
        self,
        status_code: HTTPStatus | int,
    ) -> ResponseSpec:
        status = HTTPStatus(status_code)
        schema = self.metadata.responses.get(status)
        if schema is not None:
            return schema

        allowed = set(self.metadata.responses.keys())
        raise ResponseSerializationError(
            f'Returned {status_code=} is not specified '
            f'in the list of allowed codes {allowed}',
        )

    def _validate_body(
        self,
        structured: Any | bytes,
        schema: ResponseSpec,
        *,
        response: HttpResponse | None = None,
    ) -> None:
        """
        Does structured validation based on the provided schema.

        Args:
            structured: data to be validated.
            schema: exact response description schema to be a validator.
            response: possible ``HttpResponse`` instance for validation.

        Raises:
            ResponseSerializationError: When validation fails.

        """
        if response:
            structured = self.serializer.deserialize(structured)

        try:
            self.serializer.from_python(
                structured,
                schema.return_type,
                strict=self.strict_validation,
            )
        except self.serializer.validation_error as exc:
            raise ResponseSerializationError(
                self.serializer.error_serialize(exc),
            ) from None

    def _validate_response_headers(
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response headers against provided metadata."""
        if schema.headers is None:
            metadata_headers: Set[str] = set()
        else:
            metadata_headers = schema.headers.keys()
            missing_required_headers = {
                header
                for header, response_header in schema.headers.items()
                if response_header.required
            } - response.headers.keys()
            if missing_required_headers:
                raise ResponseSerializationError(
                    'Response has missing required '
                    f'{missing_required_headers!r} headers',
                )

        extra_response_headers = (
            response.headers.keys()
            - metadata_headers
            - {'Content-Type'}  # it is added automatically
        )
        if extra_response_headers:
            raise ResponseSerializationError(
                'Response has extra undescribed '
                f'{extra_response_headers!r} headers',
            )

    def _validate_response_cookies(  # noqa: WPS210
        self,
        response: HttpResponse,
        schema: ResponseSpec,
    ) -> None:
        """Validates response cookies against provided metadata."""
        metadata_cookies = schema.cookies or {}

        # Find missing cookies:
        missing_required_cookies = {
            cookie
            for cookie, response_cookie in metadata_cookies.items()
            if response_cookie.required
        } - response.cookies.keys()
        if missing_required_cookies:
            raise ResponseSerializationError(
                'Response has missing required '
                f'{missing_required_cookies!r} cookie',
            )

        # Find extra cookies:
        extra_response_cookies = (
            response.cookies.keys() - metadata_cookies.keys()
        )
        if extra_response_cookies:
            raise ResponseSerializationError(
                'Response has extra undescribed '
                f'{extra_response_cookies!r} cookies',
            )

        # Find not fully described cookies:
        for cookie_key, cookie_body in response.cookies.items():
            if not metadata_cookies[cookie_key].is_equal(cookie_body):
                raise ResponseSerializationError(
                    f'Response cookie {cookie_key}={cookie_body!r} is not '
                    f'equal to {metadata_cookies[cookie_key]!r}',
                )


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _is_validation_enabled(
    controller: 'Controller[BaseSerializer]',
    *,
    metadata_validate_responses: bool | None,
) -> bool:
    """
    Should we run response validation?

    Priority:
    - We first return any directly specified *validate_responses*
        argument to endpoint itself
    - Second is *validate_responses* on the blueprint, if it exists
    - Then we return *validate_responses* from controller if specified
    - Lastly we return the default value from settings
    """
    if metadata_validate_responses is not None:
        return metadata_validate_responses
    if (
        controller.blueprint
        and controller.blueprint.validate_responses is not None
    ):
        return controller.blueprint.validate_responses
    if controller.validate_responses is not None:
        return controller.validate_responses
    return resolve_setting(  # type: ignore[no-any-return]
        Settings.validate_responses,
    )


class BlueprintValidator:
    """
    Validate blueprint type definition.

    Validates:
    - Async vs sync blueprints
    - Components definition
    """

    __slots__ = ()

    def __call__(self, blueprint: 'type[Blueprint[BaseSerializer]]', /) -> bool:
        """Run the validation."""
        self._validate_components(blueprint)
        is_async = self._validate_endpoints(blueprint)
        self._validate_meta_mixins(blueprint, is_async=is_async)
        self._validate_error_handlers(blueprint, is_async=is_async)
        return is_async

    def _validate_meta_mixins(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
        *,
        is_async: bool = False,
    ) -> None:
        from django_modern_rest.options_mixins import (  # noqa: PLC0415
            AsyncMetaMixin,
            MetaMixin,
        )

        if (
            issubclass(blueprint, MetaMixin)  # type: ignore[unreachable]
            and issubclass(blueprint, AsyncMetaMixin)  # type: ignore[unreachable]
        ):
            suggestion = (  # type: ignore[unreachable]
                'AsyncMetaMixin' if is_async else 'MetaMixin'
            )
            raise EndpointMetadataError(
                f'Use only {suggestion!r}, '
                f'not both meta mixins in {blueprint!r}',
            )

    def _validate_components(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
    ) -> None:
        possible_violations = infer_bases(
            blueprint,
            ComponentParser,
            use_origin=False,
        )
        for component_cls in possible_violations:
            if not get_args(component_cls):
                raise EndpointMetadataError(
                    f'Component {component_cls} in {blueprint} '
                    'must have 1 type argument, given 0',
                )

    def _validate_endpoints(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
    ) -> bool:
        if not blueprint.api_endpoints:
            return False
        is_async = blueprint.api_endpoints[
            next(iter(blueprint.api_endpoints.keys()))
        ].is_async
        if any(
            endpoint.is_async is not is_async
            for endpoint in blueprint.api_endpoints.values()
        ):
            # The same error message that django has.
            raise EndpointMetadataError(
                f'{blueprint!r} HTTP handlers must either '
                'be all sync or all async',
            )
        return is_async

    def _validate_error_handlers(
        self,
        blueprint: 'type[Blueprint[BaseSerializer]]',
        *,
        is_async: bool,
    ) -> None:
        if not blueprint.api_endpoints:
            return

        handle_error_overridden = 'handle_error' in blueprint.__dict__
        handle_async_error_overridden = (
            'handle_async_error' in blueprint.__dict__
        )

        if is_async and handle_error_overridden:
            raise EndpointMetadataError(
                f'{blueprint!r} has async endpoints but overrides '
                '`handle_error` (sync handler). '
                'Use `handle_async_error` instead for async endpoints.',
            )

        if not is_async and handle_async_error_overridden:
            raise EndpointMetadataError(
                f'{blueprint!r} has sync endpoints but overrides '
                '`handle_async_error` (async handler). '
                'Use `handle_error` instead for sync endpoints.',
            )


class ControllerValidator(BlueprintValidator):
    """
    Validates that controller is created correctly.

    Also validates possible composed blueprints.
    """

    __slots__ = ()

    @override
    def __call__(  # type: ignore[override]
        self,
        controller: type['Controller[BaseSerializer]'],
        /,
    ) -> bool:
        """Run the validation."""
        self._validate_blueprints(controller)
        self._validate_composed_endpoints(controller)
        return super().__call__(controller)

    def _validate_blueprints(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> None:
        if not controller.blueprints:
            return

        serializer = controller.blueprints[0].serializer
        for blueprint in controller.blueprints:
            if serializer is not blueprint.serializer:
                raise EndpointMetadataError(
                    'Composing blueprints with different serializer types is '
                    f'not supported: {serializer} and {blueprint.serializer}',
                )

    def _validate_composed_endpoints(
        self,
        controller: type['Controller[BaseSerializer]'],
    ) -> None:
        canonical_methods = {
            canonical for canonical, _dsl in controller.existing_http_methods()
        }
        endpoints: dict[str, Endpoint] = {}
        for blueprint in controller.blueprints:
            self._validate_blueprint(
                blueprint,
                endpoints,
                controller,
                canonical_methods,
            )
            endpoints.update(blueprint.api_endpoints)

    def _validate_blueprint(
        self,
        blueprint: type['Blueprint[BaseSerializer]'],
        endpoints: dict[str, 'Endpoint'],
        controller: type['Controller[BaseSerializer]'],
        canonical_methods: set[str],
    ) -> None:
        blueprint_methods = blueprint.api_endpoints.keys()
        if not blueprint_methods:
            raise EndpointMetadataError(
                f'{blueprint} must have at least one endpoint to be composed',
            )
        method_intersection = blueprint_methods & canonical_methods
        if method_intersection:
            raise EndpointMetadataError(
                f'{blueprint} have {method_intersection!r} common methods '
                f'with {controller}',
            )
        method_intersection = endpoints.keys() & blueprint_methods
        if method_intersection:
            raise EndpointMetadataError(
                f'Blueprints have {method_intersection!r} common methods, '
                'while all endpoints must be unique',
            )


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True, init=False)
class _OpenAPIPayload:
    summary: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    operation_id: str | None = None
    deprecated: bool = False
    security: list['SecurityRequirement'] | None = None
    external_docs: 'ExternalDocumentation | None' = None
    callbacks: 'dict[str, Callback | Reference] | None' = None
    servers: list['Server'] | None = None


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ValidateEndpointPayload(_OpenAPIPayload):
    """Payload created by ``@validate``."""

    responses: list[ResponseSpec]
    validate_responses: bool | None = None
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | None = None
    allow_custom_http_methods: bool = False


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModifyEndpointPayload(_OpenAPIPayload):
    """Payload created by ``@modify``."""

    status_code: HTTPStatus | None
    headers: Mapping[str, NewHeader] | None
    cookies: Mapping[str, NewCookie] | None
    responses: list[ResponseSpec] | None
    validate_responses: bool | None
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | None
    allow_custom_http_methods: bool


#: Alias for different payload types:
PayloadT: TypeAlias = ValidateEndpointPayload | ModifyEndpointPayload | None

#: NewType for better typing safety, don't forget to resolve all responses
#: before passing them to validation.
_AllResponses = NewType('_AllResponses', list[ResponseSpec])


class _ResponseListValidator:
    def __call__(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> dict[HTTPStatus, ResponseSpec]:
        self._validate_unique_responses(responses, endpoint=endpoint)
        self._validate_header_descriptions(responses, endpoint=endpoint)
        self._validate_cookie_descriptions(responses, endpoint=endpoint)
        self._validate_http_spec(responses, endpoint=endpoint)
        return self._convert_responses(responses)

    def _validate_unique_responses(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> None:
        # Now, check if we have any conflicts in responses.
        # For example: same status code, mismatching metadata.
        unique: dict[HTTPStatus, ResponseSpec] = {}
        for response in responses:
            existing_response = unique.get(response.status_code)
            if existing_response is not None and existing_response != response:
                raise EndpointMetadataError(
                    f'Endpoint {endpoint} has multiple responses '
                    f'for {response.status_code=}, but with different '
                    f'metadata: {response} and {existing_response}',
                )
            unique.setdefault(response.status_code, response)

    def _validate_header_descriptions(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> None:
        for response in responses:
            if response.headers is None:
                continue
            if any(
                isinstance(header, NewHeader)  # pyright: ignore[reportUnnecessaryIsInstance]
                for header in response.headers.values()
            ):
                raise EndpointMetadataError(
                    f'Cannot use `NewHeader` in {response} , '
                    f'use `HeaderSpec` instead in {endpoint!r}',
                )

    def _validate_cookie_descriptions(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> None:
        for response in responses:
            if response.headers is None:
                continue
            if any(
                header_name.lower() == 'set-cookie'
                for header_name in response.headers
            ):
                raise EndpointMetadataError(
                    f'Cannot use "Set-Cookie" header in {response}'
                    f'use `cookies=` parameter instead in {endpoint!r}.',
                )

    def _validate_http_spec(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> None:
        """Validate that we don't violate HTTP spec."""
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
        # TODO: add more checks

    def _convert_responses(
        self,
        all_responses: _AllResponses,
    ) -> dict[HTTPStatus, ResponseSpec]:
        return {resp.status_code: resp for resp in all_responses}


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class EndpointMetadataValidator:  # noqa: WPS214
    """
    Validate the metadata definition.

    It is done during import-time only once, so it can be not blazing fast.
    It is better to be precise here than to be fast.
    """

    response_list_validator_cls: ClassVar[type[_ResponseListValidator]] = (
        _ResponseListValidator
    )

    payload: PayloadT

    def __call__(
        self,
        func: Callable[..., Any],
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        controller_cls: type['Controller[BaseSerializer]'] | None,
    ) -> EndpointMetadata:
        """Do the validation."""
        # TODO: validate that we can't specify `Set-Cookie` header.
        # You should use `cookies=` instead.
        return_annotation = parse_return_annotation(func)
        if self.payload is None and is_safe_subclass(
            return_annotation,
            HttpResponse,
        ):
            object.__setattr__(
                self,
                'payload',
                ValidateEndpointPayload(responses=[]),
            )
        method = validate_method_name(
            func.__name__,
            allow_custom_http_methods=getattr(
                self.payload,
                'allow_custom_http_methods',
                False,
            ),
        )
        func.__name__ = method  # we can change it :)
        endpoint = str(func)
        if isinstance(self.payload, ValidateEndpointPayload):
            return self._from_validate(
                self.payload,
                return_annotation,
                method,
                func,
                endpoint=endpoint,
                blueprint_cls=blueprint_cls,
                controller_cls=controller_cls,
            )
        if isinstance(self.payload, ModifyEndpointPayload):
            return self._from_modify(
                self.payload,
                return_annotation,
                method,
                func,
                endpoint=endpoint,
                blueprint_cls=blueprint_cls,
                controller_cls=controller_cls,
            )
        if self.payload is None:
            return self._from_raw_data(
                return_annotation,
                method,
                endpoint=endpoint,
                blueprint_cls=blueprint_cls,
                controller_cls=controller_cls,
            )
        assert_never(self.payload)

    def _resolve_all_responses(
        self,
        endpoint_responses: list[ResponseSpec],
        *,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        controller_cls: type['Controller[BaseSerializer]'] | None,
        modification: ResponseModification | None = None,
    ) -> _AllResponses:
        modification_spec = [modification.to_spec()] if modification else []
        return cast(
            '_AllResponses',
            [
                *modification_spec,
                *endpoint_responses,
                *blueprint_cls.semantic_responses(),
                *(
                    []
                    if controller_cls is None
                    else controller_cls.semantic_responses()
                ),
                *resolve_setting(Settings.responses),
            ],
        )

    def _from_validate(  # noqa: WPS211
        self,
        payload: ValidateEndpointPayload,
        return_annotation: Any,
        method: str,
        func: Callable[..., Any],
        *,
        endpoint: str,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        controller_cls: type['Controller[BaseSerializer]'] | None,
    ) -> EndpointMetadata:
        self._validate_error_handler(payload, func, endpoint=endpoint)
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
        )
        all_responses = self._resolve_all_responses(
            payload.responses,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
        )
        responses = self.response_list_validator_cls()(
            all_responses,
            endpoint=endpoint,
        )
        return EndpointMetadata(
            responses=responses,
            method=method,
            validate_responses=payload.validate_responses,
            modification=None,
            error_handler=payload.error_handler,
            component_parsers=blueprint_cls._component_parsers,  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            summary=payload.summary,
            description=payload.description,
            tags=payload.tags,
            operation_id=payload.operation_id,
            deprecated=payload.deprecated,
            security=payload.security,
            external_docs=payload.external_docs,
            callbacks=payload.callbacks,
            servers=payload.servers,
        )

    def _from_modify(  # noqa: WPS211
        self,
        payload: ModifyEndpointPayload,
        return_annotation: Any,
        method: str,
        func: Callable[..., Any],
        *,
        endpoint: str,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        controller_cls: type['Controller[BaseSerializer]'] | None,
    ) -> EndpointMetadata:
        self._validate_error_handler(payload, func, endpoint=endpoint)
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
        )
        self._validate_new_headers(payload, endpoint=endpoint)
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
        if payload.responses is None:
            payload_responses = []
        else:
            payload_responses = payload.responses
        all_responses = self._resolve_all_responses(
            payload_responses,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
            modification=modification,
        )
        responses = self.response_list_validator_cls()(
            all_responses,
            endpoint=endpoint,
        )
        return EndpointMetadata(
            responses=responses,
            validate_responses=payload.validate_responses,
            method=method,
            modification=modification,
            error_handler=payload.error_handler,
            component_parsers=blueprint_cls._component_parsers,  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            summary=payload.summary,
            description=payload.description,
            tags=payload.tags,
            operation_id=payload.operation_id,
            deprecated=payload.deprecated,
            security=payload.security,
            external_docs=payload.external_docs,
            callbacks=payload.callbacks,
            servers=payload.servers,
        )

    def _from_raw_data(
        self,
        return_annotation: Any,
        method: str,
        *,
        endpoint: str,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        controller_cls: type['Controller[BaseSerializer]'] | None,
    ) -> EndpointMetadata:
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
        )
        status_code = infer_status_code(method)
        modification = ResponseModification(
            return_type=return_annotation,
            status_code=status_code,
            headers=None,
            cookies=None,
        )
        all_responses = self._resolve_all_responses(
            [],
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
            modification=modification,
        )
        responses = self.response_list_validator_cls()(
            all_responses,
            endpoint=endpoint,
        )
        return EndpointMetadata(
            responses=responses,
            validate_responses=None,
            method=method,
            modification=modification,
            error_handler=None,
            component_parsers=blueprint_cls._component_parsers,  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        )

    def _validate_new_headers(
        self,
        payload: ModifyEndpointPayload,
        *,
        endpoint: str,
    ) -> None:
        if payload.headers is not None and any(
            isinstance(header, HeaderSpec)  # pyright: ignore[reportUnnecessaryIsInstance]
            for header in payload.headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns raw data, '
                f'it is not possible to use `HeaderSpec` '
                'because there are no existing headers to describe. Use '
                '`NewHeader` to add new headers to the response',
            )

    def _validate_return_annotation(
        self,
        return_annotation: Any,
        *,
        endpoint: str,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        controller_cls: type['Controller[BaseSerializer]'] | None,
    ) -> None:
        if is_safe_subclass(return_annotation, HttpResponse):
            if isinstance(self.payload, ModifyEndpointPayload):
                raise EndpointMetadataError(
                    f'{endpoint!r} returns HttpResponse '
                    'it requires `@validate` decorator instead of `@modify`',
                )
            # We can't reach this point with `None`, it is processed before.
            assert isinstance(self.payload, ValidateEndpointPayload)  # noqa: S101
            if not self._resolve_all_responses(
                self.payload.responses,
                blueprint_cls=blueprint_cls,
                controller_cls=controller_cls,
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

    def _validate_error_handler(
        self,
        payload: ValidateEndpointPayload | ModifyEndpointPayload,
        func: Callable[..., Any],
        *,
        endpoint: str,
    ) -> None:
        if payload.error_handler is None:
            return
        if inspect.iscoroutinefunction(func):
            if not inspect.iscoroutinefunction(payload.error_handler):
                raise EndpointMetadataError(
                    f'Cannot pass sync `error_handler` to async {endpoint}',
                )
        elif inspect.iscoroutinefunction(payload.error_handler):
            raise EndpointMetadataError(
                f'Cannot pass async `error_handler` to sync {endpoint}',
            )

    # TODO: Does we need extract methods for summary and
    # description from endpoint.__doc__?


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
    headers: dict[str, str]
    cookies: Mapping[str, NewCookie] | None


def validate_method_name(
    func_name: str,
    *,
    allow_custom_http_methods: bool,
) -> str:
    """Validates that a function has correct HTTP method name."""
    try:  # noqa: WPS229
        if func_name != func_name.lower():
            raise ValueError  # noqa: TRY301
        if func_name == 'meta':
            return 'options'
        if allow_custom_http_methods:
            return func_name
        return HTTPMethod(func_name.upper()).value.lower()
    except ValueError:
        raise EndpointMetadataError(
            f'{func_name} is not a valid HTTP method name',
        ) from None
