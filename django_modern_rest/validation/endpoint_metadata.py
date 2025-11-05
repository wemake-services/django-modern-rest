import dataclasses
import inspect
from collections.abc import Callable, Set
from http import HTTPMethod, HTTPStatus
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NewType,
    assert_never,
    cast,
)

from django.http import HttpResponse

from django_modern_rest.cookies import CookieSpec, NewCookie
from django_modern_rest.exceptions import (
    EndpointMetadataError,
)
from django_modern_rest.headers import (
    HeaderSpec,
    NewHeader,
)
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.response import (
    ResponseModification,
    ResponseSpec,
    infer_status_code,
)
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.settings import (
    HttpSpec,
    Settings,
    resolve_setting,
)
from django_modern_rest.types import (
    is_safe_subclass,
    parse_return_annotation,
)
from django_modern_rest.validation.payload import (
    ModifyEndpointPayload,
    PayloadT,
    ValidateEndpointPayload,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller

#: NewType for better typing safety, don't forget to resolve all responses
#: before passing them to validation.
_AllResponses = NewType('_AllResponses', list[ResponseSpec])


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class _ResponseListValidator:
    """Validates responses metadata."""

    payload: PayloadT
    blueprint_cls: type['Blueprint[BaseSerializer]'] | None
    controller_cls: type['Controller[BaseSerializer]']
    endpoint: str

    def __call__(
        self,
        responses: _AllResponses,
    ) -> dict[HTTPStatus, ResponseSpec]:
        self._validate_unique_responses(responses)
        self._validate_header_descriptions(responses)
        self._validate_cookie_descriptions(responses)
        self._validate_cookie_spec_in_responses(responses)
        if isinstance(self.payload, ModifyEndpointPayload):
            self._validate_new_cookie_in_modify(
                self.payload,
                endpoint=self.endpoint,
            )
        self._validate_http_spec(responses)
        return self._convert_responses(responses)

    def _validate_unique_responses(
        self,
        responses: _AllResponses,
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

    def _validate_header_descriptions(
        self,
        responses: _AllResponses,
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
                    f'use `HeaderSpec` instead in {self.endpoint!r}',
                )

    def _validate_cookie_spec_in_responses(
        self,
        responses: _AllResponses,
    ) -> None:
        for response in responses:
            if response.cookies is None:
                continue
            if any(
                isinstance(cookie, NewCookie)
                # pyright: ignore[reportUnnecessaryIsInstance]
                for cookie in response.cookies.values()
            ):
                raise EndpointMetadataError(
                    f'Cannot use `NewCookie` in {response} , '
                    f'use `CookieSpec` instead in {self.endpoint!r}',
                )

    def _validate_new_cookie_in_modify(
        self,
        payload: ModifyEndpointPayload,
        *,
        endpoint: str,
    ) -> None:
        if payload.cookies is not None and any(
            isinstance(cookie, CookieSpec)
            # pyright: ignore[reportUnnecessaryIsInstance]
            for cookie in payload.cookies.values()
        ):
            raise EndpointMetadataError(
                f'Since {endpoint!r} returns raw data, '
                f'it is not possible to use `CookieSpec` '
                'because there are no existing headers to describe. Use '
                '`NewCookie` to add new cookies to the response',
            )

    def _validate_cookie_descriptions(
        self,
        responses: _AllResponses,
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
                    f'use `cookies=` parameter instead in {self.endpoint!r}',
                )

    def _validate_http_spec(
        self,
        responses: _AllResponses,
    ) -> None:
        """Validate that we don't violate HTTP spec."""
        # TODO: turn into a decorator
        payload_items = (
            None if self.payload is None else self.payload.no_validate_http_spec
        )
        if _is_check_enabled(
            HttpSpec.empty_response_body,
            payload_items,
            self.blueprint_cls,
            self.controller_cls,
        ):
            _validate_empty_response_body(responses, endpoint=self.endpoint)
        # TODO: add more checks

    def _convert_responses(
        self,
        all_responses: _AllResponses,
    ) -> dict[HTTPStatus, ResponseSpec]:
        return {resp.status_code: resp for resp in all_responses}


def _validate_empty_response_body(
    responses: _AllResponses,
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


def _is_check_enabled(
    setting: HttpSpec,
    payload_value: Set[HttpSpec] | None,
    blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
    controller_cls: type['Controller[BaseSerializer]'],
) -> bool:
    if payload_value is not None and setting in payload_value:
        return False
    if (
        blueprint_cls is not None
        and setting in blueprint_cls.no_validate_http_spec
    ):
        return False
    if setting in controller_cls.no_validate_http_spec:
        return False
    return setting not in resolve_setting(Settings.no_validate_http_spec)


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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
        modification: ResponseModification | None = None,
    ) -> _AllResponses:
        return cast(
            '_AllResponses',
            [
                *([] if modification is None else [modification.to_spec()]),
                *endpoint_responses,
                *(
                    []
                    if blueprint_cls is None
                    else blueprint_cls.semantic_responses()
                ),
                *controller_cls.semantic_responses(),
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
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
        responses = self.response_list_validator_cls(
            payload=payload,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
            endpoint=endpoint,
        )(all_responses)
        return EndpointMetadata(
            responses=responses,
            method=method,
            validate_responses=payload.validate_responses,
            modification=None,
            error_handler=payload.error_handler,
            component_parsers=(
                (blueprint_cls or controller_cls)._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            ),
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
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
        responses = self.response_list_validator_cls(
            payload=payload,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
            endpoint=endpoint,
        )(all_responses)
        return EndpointMetadata(
            responses=responses,
            validate_responses=payload.validate_responses,
            method=method,
            modification=modification,
            error_handler=payload.error_handler,
            component_parsers=(
                (blueprint_cls or controller_cls)._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            ),
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
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
        responses = self.response_list_validator_cls(
            payload=None,
            blueprint_cls=blueprint_cls,
            controller_cls=controller_cls,
            endpoint=endpoint,
        )(all_responses)
        return EndpointMetadata(
            responses=responses,
            validate_responses=None,
            method=method,
            modification=modification,
            error_handler=None,
            component_parsers=(
                (blueprint_cls or controller_cls)._component_parsers  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            ),
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
        blueprint_cls: type['Blueprint[BaseSerializer]'] | None,
        controller_cls: type['Controller[BaseSerializer]'],
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


def validate_method_name(
    func_name: str,
    *,
    allow_custom_http_methods: bool,
) -> str:
    """Validates that a function has correct HTTP method name."""
    if func_name != func_name.lower():
        raise EndpointMetadataError(
            f'{func_name} is not a valid HTTP method name',
        )
    if func_name == 'meta':
        return 'options'
    if allow_custom_http_methods:
        return func_name

    try:
        return HTTPMethod(func_name.upper()).value.lower()
    except ValueError:
        raise EndpointMetadataError(
            f'{func_name} is not a valid HTTP method name',
        ) from None
