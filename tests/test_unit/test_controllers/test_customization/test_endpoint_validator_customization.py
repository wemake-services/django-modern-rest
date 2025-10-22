from collections.abc import Callable
from http import HTTPStatus
from typing import Any, ClassVar, final

from typing_extensions import override

from django_modern_rest import APIError, Controller
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serialization import BaseSerializer
from django_modern_rest.test import DMRRequestFactory
from django_modern_rest.validation import (
    EndpointMetadataValidator,
    ResponseValidator,
    _ResponseT,
)


@final
class _CustomEndpointMetadataValidator(EndpointMetadataValidator):
    was_called: ClassVar[bool] = False

    @override
    def __call__(
        self,
        func: Callable[..., Any],
        controller_cls: type[Controller[BaseSerializer]],
    ) -> EndpointMetadata:
        self.__class__.was_called = True
        return super().__call__(func, controller_cls)


@final
class _CustomResponseValidator(ResponseValidator):
    was_called: ClassVar[bool] = False

    @override
    def validate_response(
        self,
        controller: Controller[BaseSerializer],
        response: _ResponseT,
    ) -> _ResponseT:
        self.__class__.was_called = True
        return super().validate_response(controller, response)


@final
class _CustomEndpoint(Endpoint):
    metadata_validator_cls: ClassVar[type[EndpointMetadataValidator]] = (
        _CustomEndpointMetadataValidator
    )
    response_validator_cls: ClassVar[type[ResponseValidator]] = (
        _CustomResponseValidator
    )


@final
class _CustomController(Controller[PydanticSerializer]):
    endpoint_cls: ClassVar[type[Endpoint]] = _CustomEndpoint

    def get(self) -> int:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)


def test_endpoint_metadata_validator() -> None:
    """Ensures custom endpoint metadata validator is called."""
    assert _CustomEndpointMetadataValidator.was_called is True


def test_endpoint_response_validator(dmr_rf: DMRRequestFactory) -> None:
    """Ensures custom response validator is called during request processing."""
    assert _CustomResponseValidator.was_called is False

    request = dmr_rf.get('/whatever/')
    _CustomController.as_view()(request)
    assert _CustomResponseValidator.was_called is True
