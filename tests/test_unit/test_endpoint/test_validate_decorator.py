from http import HTTPStatus

import pytest
from django.http import HttpResponse

from django_modern_rest import Controller, validate
from django_modern_rest.exceptions import MissingEndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer


def test_validate_required_for_responses() -> None:
    """Ensures `@validate` is required for `HttpResponse` returns."""
    with pytest.raises(MissingEndpointMetadataError, match='@validate'):

        class _NoDecorator(Controller[PydanticSerializer]):
            def get(self) -> HttpResponse:
                raise NotImplementedError


def test_validate_on_non_response() -> None:
    """Ensures `@validate` can't be used on regular return types."""
    with pytest.raises(MissingEndpointMetadataError, match='@validate'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @validate(  # type: ignore[type-var]
                return_type=str,
                status_code=HTTPStatus.OK,
            )
            def get(self) -> str:
                raise NotImplementedError
