from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpResponse

from django_modern_rest import (
    Blueprint,
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.settings import HttpSpec


@pytest.mark.parametrize(
    'status',
    [HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED],
)
@pytest.mark.parametrize(
    'base_class',
    [Controller[PydanticSerializer], Blueprint[PydanticSerializer]],
)
def test_empty_response_body(
    *,
    status: HTTPStatus,
    base_class: type[Any],
) -> None:
    """Ensure that some statuses must not have bodies."""
    with pytest.raises(EndpointMetadataError, match='return `None` not'):

        class _Mixed(base_class):  # type: ignore[misc]
            responses = [
                ResponseSpec(int, status_code=status),
            ]
            no_validate_http_spec = {HttpSpec.empty_request_body}

            def get(self) -> str:  # needs at least one endpoint to validate
                raise NotImplementedError


@pytest.mark.parametrize(
    'status',
    [HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED],
)
@pytest.mark.parametrize(
    'base_class',
    [Controller[PydanticSerializer], Blueprint[PydanticSerializer]],
)
def test_empty_response_body_disabled(
    *,
    status: HTTPStatus,
    base_class: type[Any],
) -> None:
    """Ensure that can be disabled on class level."""

    class _Mixed(base_class):  # type: ignore[misc]
        responses = [
            ResponseSpec(int, status_code=status),
        ]
        no_validate_http_spec = {HttpSpec.empty_response_body}

        def get(self) -> str:  # needs at least one endpoint to validate
            raise NotImplementedError

    assert _Mixed.no_validate_http_spec


@pytest.mark.parametrize(
    'status',
    [HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED],
)
def test_empty_response_body_modify(
    *,
    status: HTTPStatus,
) -> None:
    """Ensure that can be disabled on modify level."""

    class _Mixed(Controller[PydanticSerializer]):
        @modify(
            extra_responses=[
                ResponseSpec(int, status_code=status),
            ],
            no_validate_http_spec={HttpSpec.empty_response_body},
        )
        def get(self) -> str:
            raise NotImplementedError


@pytest.mark.parametrize(
    'status',
    [HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED],
)
def test_empty_response_body_validate(
    *,
    status: HTTPStatus,
) -> None:
    """Ensure that can be disabled on validate level."""

    class _Mixed(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(int, status_code=status),
            no_validate_http_spec={HttpSpec.empty_response_body},
        )
        def get(self) -> HttpResponse:
            raise NotImplementedError
