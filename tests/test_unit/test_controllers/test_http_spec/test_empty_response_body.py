from http import HTTPStatus

import pytest
from django.http import HttpResponse

from dmr import (
    Blueprint,
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec


@pytest.mark.parametrize(
    'status',
    [HTTPStatus.NO_CONTENT, HTTPStatus.NOT_MODIFIED],
)
def test_empty_response_body(
    *,
    status: HTTPStatus,
) -> None:
    """Ensure that some statuses must not have bodies."""
    with pytest.raises(EndpointMetadataError, match='return `None` not'):

        class _Mixed(Controller[PydanticSerializer]):
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
def test_empty_response_body_controller(
    *,
    status: HTTPStatus,
) -> None:
    """Ensure that can be disabled on controller level."""

    class _Mixed(Controller[PydanticSerializer]):
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
def test_empty_response_body_blueprint(
    *,
    status: HTTPStatus,
) -> None:
    """Ensure that can be disabled on blueprint level."""

    class _Blueprint(Blueprint[PydanticSerializer]):
        responses = [
            ResponseSpec(int, status_code=status),
        ]
        no_validate_http_spec = {HttpSpec.empty_response_body}

        def get(self) -> str:  # needs at least one endpoint to validate
            raise NotImplementedError

    class _Mixed(Controller[PydanticSerializer]):
        blueprints = [_Blueprint]

    assert _Mixed.api_endpoints['GET'].metadata.responses

    # But, controllers are not affected by `Blueprint` level:
    with pytest.raises(EndpointMetadataError, match=str(status)):

        class _BadController(Controller[PydanticSerializer]):
            blueprints = [_Blueprint]

            @modify(status_code=status)
            def post(self) -> int:
                raise NotImplementedError


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
