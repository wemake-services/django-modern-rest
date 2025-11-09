from collections.abc import Callable
from http import HTTPStatus
from typing import Any, ClassVar, final

from django.http import HttpResponse
from typing_extensions import override

from django_modern_rest import APIError, Blueprint, Controller, ResponseSpec
from django_modern_rest.endpoint import (
    Endpoint,
    HttpResponseValidatorCls,
    RawResponseValidatorCls,
    validate,
)
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.test import DMRRequestFactory
from django_modern_rest.validation import (
    EndpointMetadataValidator,
)
from django_modern_rest.validation.response import (
    HttpResponseValidator,
    RawResponseValidator,
)


@final
class _CustomEndpointMetadataValidator(EndpointMetadataValidator):
    was_called: ClassVar[bool] = False

    @override
    def __call__(
        self,
        func: Callable[..., Any],
        blueprint_cls: type[Blueprint[BaseSerializer]] | None,
        controller_cls: type[Controller[BaseSerializer]],
    ) -> EndpointMetadata:
        self.__class__.was_called = True
        return super().__call__(func, blueprint_cls, controller_cls)


@final
class _CustomHttpResponseValidator(HttpResponseValidator):
    was_called: ClassVar[bool] = False

    @override
    def validate(
        self,
        controller: Controller[BaseSerializer],
        response_content: HttpResponse,
    ) -> HttpResponse:
        self.__class__.was_called = True
        return super().validate(controller, response_content)


@final
class _CustomRawResponseValidator(RawResponseValidator):
    was_called: ClassVar[bool] = False

    @override
    def validate(
        self,
        controller: Controller[BaseSerializer],
        response_content: Any,
    ) -> HttpResponse:
        self.__class__.was_called = True
        return super().validate(controller, response_content)


@final
class _CustomEndpoint(Endpoint):
    metadata_validator_cls: ClassVar[type[EndpointMetadataValidator]] = (
        _CustomEndpointMetadataValidator
    )
    http_response_validator_cls: ClassVar[HttpResponseValidatorCls] = (
        _CustomHttpResponseValidator
    )
    raw_response_validator_cls: ClassVar[RawResponseValidatorCls] = (
        _CustomRawResponseValidator
    )


@final
class _CustomController(Controller[PydanticSerializer]):
    endpoint_cls: ClassVar[type[Endpoint]] = _CustomEndpoint

    def get(self) -> int:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @validate(
        ResponseSpec(
            return_type=list[int],
            status_code=HTTPStatus.OK,
        ),
    )
    def post(self) -> HttpResponse:
        return self.to_response(
            raw_data=[1, 2],
            status_code=HTTPStatus.OK,
        )


def test_endpoint_metadata_validator() -> None:
    """Ensures custom endpoint metadata validator is called."""
    assert _CustomEndpointMetadataValidator.was_called is True


def test_endpoint_http_response_validator(dmr_rf: DMRRequestFactory) -> None:
    """
    Ensures custom http response validator is called during request processing.
    """  # noqa: D200
    assert _CustomHttpResponseValidator.was_called is False

    request = dmr_rf.post('/whatever/')
    _CustomController.as_view()(request)
    assert _CustomHttpResponseValidator.was_called is True


def test_endpoint_raw_response_validator(dmr_rf: DMRRequestFactory) -> None:
    """
    Ensures custom raw response validator is called during request processing.
    """  # noqa: D200
    assert _CustomRawResponseValidator.was_called is False

    request = dmr_rf.get('/whatever/')
    _CustomController.as_view()(request)
    assert _CustomRawResponseValidator.was_called is True
