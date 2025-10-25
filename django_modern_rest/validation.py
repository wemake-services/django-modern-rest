import dataclasses
import inspect
from collections import Counter
from collections.abc import Callable, Mapping, Set
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

from django_modern_rest.components import ComponentParser
from django_modern_rest.errors import AsyncErrorHandlerT, SyncErrorHandlerT
from django_modern_rest.exceptions import (
    EndpointMetadataError,
    ResponseSerializationError,
)
from django_modern_rest.headers import (
    HeaderDescription,
    NewHeader,
    build_headers,
)
from django_modern_rest.metadata import (
    EndpointMetadata,
)
from django_modern_rest.response import (
    ResponseDescription,
    ResponseModification,
    infer_status_code,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    DMR_RESPONSES_KEY,
    DMR_VALIDATE_RESPONSES_KEY,
    resolve_setting,
)
from django_modern_rest.types import (
    Empty,
    EmptyObj,
    infer_bases,
    is_safe_subclass,
    parse_return_annotation,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller

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
        if not self._is_validation_enabled(controller):
            return response
        schema = self._get_response_schema(controller, response.status_code)
        self._validate_body(response.content, schema, response=response)
        self._validate_response_object(response, schema)
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
                f'Controller {controller} in {method} returned '
                f'raw data of type {type(structured)} '
                'without associated `@modify` usage.',
            )

        all_response_data = _ValidationContext(
            raw_data=structured,
            status_code=self.metadata.modification.status_code,
            headers=build_headers(
                self.metadata.modification.headers,
                self.serializer,
            ),
        )
        if not self._is_validation_enabled(controller):
            return all_response_data
        schema = self._get_response_schema(
            controller,
            all_response_data.status_code,
        )
        self._validate_body(structured, schema)
        return all_response_data

    def _get_response_schema(
        self,
        controller: 'Controller[BaseSerializer]',
        status_code: HTTPStatus | int,
    ) -> ResponseDescription:
        status = HTTPStatus(status_code)
        schema = self.metadata.responses.get(status)
        if schema is not None:
            return schema

        allowed = set(self.metadata.responses.keys())
        raise ResponseSerializationError(
            f'Returned {status_code=} is not specified '
            f'in the list of allowed codes {allowed}',
        )

    def _is_validation_enabled(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> bool:
        """
        Should we run response validation?

        Priority:
        - We first return any directly specified *validate_responses*
          argument to endpoint itself
        - Then we return *validate_responses* from controller if specified
        - Lastly we return the default value from settings
        """
        if isinstance(self.metadata.validate_responses, bool):
            return self.metadata.validate_responses
        if isinstance(controller.validate_responses, bool):
            return controller.validate_responses
        return resolve_setting(  # type: ignore[no-any-return]
            DMR_VALIDATE_RESPONSES_KEY,
        )

    def _validate_body(
        self,
        structured: Any | bytes,
        schema: ResponseDescription,
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

    def _validate_response_object(
        self,
        response: HttpResponse,
        schema: ResponseDescription,
    ) -> None:
        """Validates response against provided metadata."""
        # Validate headers, at this point we know
        # that only `HeaderDescription` can be in `metadata.headers`:
        if isinstance(schema.headers, Empty):
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


class ControllerValidator:
    """
    Validate controller type definition.

    Validates:
    - Async vs sync controllers
    - Components definition
    """

    __slots__ = ()

    def __call__(self, controller: 'type[Controller[BaseSerializer]]') -> bool:
        """Run the validation."""
        self._validate_components(controller)
        is_async = self._validate_endpoints(controller)
        self._validate_meta_mixins(controller, is_async=is_async)
        return is_async

    def _validate_meta_mixins(
        self,
        controller: 'type[Controller[BaseSerializer]]',
        *,
        is_async: bool = False,
    ) -> None:
        from django_modern_rest.options_mixins import (  # noqa: PLC0415
            AsyncMetaMixin,
            MetaMixin,
        )

        if (
            issubclass(controller, MetaMixin)
            and issubclass(controller, AsyncMetaMixin)  # type: ignore[unreachable]
        ):
            suggestion = (  # type: ignore[unreachable]
                'AsyncMetaMixin' if is_async else 'MetaMixin'
            )
            raise EndpointMetadataError(
                f'Use only {suggestion!r}, '
                f'not both meta mixins in {controller!r}',
            )

    def _validate_components(
        self,
        controller: 'type[Controller[BaseSerializer]]',
    ) -> None:
        possible_violations = infer_bases(
            controller,
            ComponentParser,
            use_origin=False,
        )
        for component_cls in possible_violations:
            if not get_args(component_cls):
                raise EndpointMetadataError(
                    f'Component {component_cls} in {controller} '
                    'must have 1 type argument, given 0',
                )

    def _validate_endpoints(
        self,
        controller: 'type[Controller[BaseSerializer]]',
    ) -> bool:
        if not controller.api_endpoints:
            return False
        is_async = controller.api_endpoints[
            next(iter(controller.api_endpoints.keys()))
        ].is_async
        if any(
            endpoint.is_async is not is_async
            for endpoint in controller.api_endpoints.values()
        ):
            # The same error message that django has.
            raise EndpointMetadataError(
                f'{controller!r} HTTP handlers must either '
                'be all sync or all async',
            )
        return is_async


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ValidateEndpointPayload:
    """Payload created by ``@validate``."""

    responses: list[ResponseDescription]
    validate_responses: bool | Empty
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | Empty
    allow_custom_http_methods: bool


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ModifyEndpointPayload:
    """Payload created by ``@modify``."""

    status_code: HTTPStatus | Empty
    headers: Mapping[str, NewHeader] | Empty
    responses: list[ResponseDescription] | Empty
    validate_responses: bool | Empty
    error_handler: SyncErrorHandlerT | AsyncErrorHandlerT | Empty
    allow_custom_http_methods: bool


#: Alias for different payload types:
PayloadT: TypeAlias = ValidateEndpointPayload | ModifyEndpointPayload | None

#: NewType for better typing safety, don't forget to resolve all responses
#: before passing them to validation.
_AllResponses = NewType('_AllResponses', list[ResponseDescription])


class _ResponseListValidator:
    def __call__(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> dict[HTTPStatus, ResponseDescription]:
        self._validate_unique_responses(responses, endpoint=endpoint)
        self._validate_header_descriptions(responses, endpoint=endpoint)
        self._validate_http_spec(responses, endpoint=endpoint)
        return self._convert_responses(responses)

    def _validate_unique_responses(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> None:
        counter = Counter(response.status_code for response in responses)
        for status, count in counter.items():
            if count > 1:
                raise EndpointMetadataError(
                    f'{endpoint!r} has {status} specified {count} times',
                )

    def _validate_header_descriptions(
        self,
        responses: _AllResponses,
        *,
        endpoint: str,
    ) -> None:
        for response in responses:
            if isinstance(response.headers, Empty):
                continue
            if any(
                isinstance(header, NewHeader)  # pyright: ignore[reportUnnecessaryIsInstance]
                for header in response.headers.values()
            ):
                raise EndpointMetadataError(
                    f'Cannot use `NewHeader` in {response} , '
                    f'use `HeaderDescription` instead in {endpoint!r}',
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
    ) -> dict[HTTPStatus, ResponseDescription]:
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
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> EndpointMetadata:
        """Do the validation."""
        return_annotation = parse_return_annotation(func)
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
        if isinstance(self.payload, ModifyEndpointPayload):
            return self._from_modify(
                self.payload,
                return_annotation,
                method,
                func,
                endpoint=endpoint,
                controller_cls=controller_cls,
            )
        if isinstance(self.payload, ValidateEndpointPayload):
            return self._from_validate(
                self.payload,
                return_annotation,
                method,
                func,
                endpoint=endpoint,
                controller_cls=controller_cls,
            )
        if self.payload is None:
            return self._from_raw_data(
                return_annotation,
                method,
                endpoint=endpoint,
                controller_cls=controller_cls,
            )
        assert_never(self.payload)

    def _resolve_all_responses(
        self,
        endpoint_responses: list[ResponseDescription],
        *,
        controller_cls: type['Controller[BaseSerializer]'],
        modification: ResponseModification | None = None,
    ) -> _AllResponses:
        modification_spec = (
            [modification.to_description()] if modification else []
        )
        return cast(
            '_AllResponses',
            [
                *modification_spec,
                *endpoint_responses,
                *controller_cls.semantic_responses(),
                *resolve_setting(DMR_RESPONSES_KEY),
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
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> EndpointMetadata:
        self._validate_error_handler(payload, func, endpoint=endpoint)
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            needs_response=True,
        )
        # for mypy: this can't happen, we always have at least one response
        # due to `@validate`'s signature.
        assert payload.responses, f'No responses found for {endpoint!r}'  # noqa: S101
        all_responses = self._resolve_all_responses(
            payload.responses,
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
        )

    def _from_modify(  # noqa: WPS211
        self,
        payload: ModifyEndpointPayload,
        return_annotation: Any,
        method: str,
        func: Callable[..., Any],
        *,
        endpoint: str,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> EndpointMetadata:
        self._validate_error_handler(payload, func, endpoint=endpoint)
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            needs_response=False,
            modify_used=True,
        )
        self._validate_new_headers(payload, endpoint=endpoint)
        modification = ResponseModification(
            return_type=return_annotation,
            headers=payload.headers,
            status_code=(
                infer_status_code(method)
                if isinstance(payload.status_code, Empty)
                else payload.status_code
            ),
        )
        if isinstance(payload.responses, Empty):
            payload_responses = []
        else:
            payload_responses = payload.responses
        all_responses = self._resolve_all_responses(
            payload_responses,
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
        )

    def _from_raw_data(
        self,
        return_annotation: Any,
        method: str,
        *,
        endpoint: str,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> EndpointMetadata:
        self._validate_return_annotation(
            return_annotation,
            endpoint=endpoint,
            needs_response=False,
        )
        status_code = infer_status_code(method)
        modification = ResponseModification(
            return_type=return_annotation,
            status_code=status_code,
            headers=EmptyObj,
        )
        all_responses = self._resolve_all_responses(
            [],
            controller_cls=controller_cls,
            modification=modification,
        )
        responses = self.response_list_validator_cls()(
            all_responses,
            endpoint=endpoint,
        )
        return EndpointMetadata(
            responses=responses,
            validate_responses=EmptyObj,
            method=method,
            modification=modification,
            error_handler=EmptyObj,
        )

    def _validate_new_headers(
        self,
        payload: ModifyEndpointPayload,
        *,
        endpoint: str,
    ) -> None:
        if not isinstance(payload.headers, Empty) and any(
            isinstance(header, HeaderDescription)  # pyright: ignore[reportUnnecessaryIsInstance]
            for header in payload.headers.values()
        ):
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns raw data, '
                f'it is not possible to use `HeaderDescription` '
                'because there are no existing headers to describe. Use '
                '`NewHeader` to add new headers to the response',
            )

    def _validate_return_annotation(
        self,
        return_annotation: Any,
        *,
        endpoint: str,
        needs_response: bool,
        modify_used: bool = False,
    ) -> None:
        if is_safe_subclass(return_annotation, HttpResponse):
            if needs_response:
                return
            part = ' instead of `@modify`' if modify_used else ''
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns HttpResponse, '  # noqa: WPS226
                f'it requires `@validate` decorator{part}',
            )
        if not needs_response:
            return
        raise EndpointMetadataError(
            f'Since {endpoint!r} returns regular data, '
            'it requires `@modify` decorator instead of `@validate`',
        )

    def _validate_error_handler(
        self,
        payload: ValidateEndpointPayload | ModifyEndpointPayload,
        func: Callable[..., Any],
        *,
        endpoint: str,
    ) -> None:
        if isinstance(payload.error_handler, Empty):
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


@final
@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ValidationContext:
    """Combines all validated data together."""

    raw_data: Any  # not empty
    status_code: HTTPStatus
    headers: dict[str, str]


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
