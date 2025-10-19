import json
from http import HTTPMethod, HTTPStatus

import pytest
from django.http import HttpResponse

from django_modern_rest import (
    Controller,
    HeaderDescription,
    ResponseDescription,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _CorrectToResponseController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.ACCEPTED,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def get(self) -> HttpResponse:
        """Tests that `.to_response` works correctly."""
        return self.to_response(
            ['a', 'b'],
            headers={'X-Custom': 'value'},
            status_code=HTTPStatus.ACCEPTED,
        )

    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.CREATED,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def post(self) -> HttpResponse:
        """Tests that `.to_response` works with extra headers."""
        return self.to_response(
            ['a', 'b'],
            headers={'X-Custom': 'value', 'Content-Type': 'application/json5'},
        )

    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.OK,
        ),
    )
    def delete(self) -> HttpResponse:
        """Minimal version."""
        return self.to_response(['a', 'b'])


class _WrongToResponseController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.ACCEPTED,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def post(self) -> HttpResponse:
        """Wrong body format."""
        return self.to_response(
            [1, 2],
            headers={'X-Custom': 'value'},
            status_code=HTTPStatus.ACCEPTED,
        )

    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.ACCEPTED,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def put(self) -> HttpResponse:
        """Wrong headers."""
        return self.to_response(
            ['a', 'b'],
            status_code=HTTPStatus.ACCEPTED,
        )

    @validate(
        ResponseDescription(
            return_type=list[str],
            status_code=HTTPStatus.ACCEPTED,
            headers={'X-Custom': HeaderDescription()},
        ),
    )
    def patch(self) -> HttpResponse:
        """Wrong status code."""
        return self.to_response(
            ['a', 'b'],
            headers={'X-Custom': 'value'},
        )


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_to_response_fails_validation(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response headers are validated."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongToResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    ('method', 'headers', 'status_code'),
    [
        (
            HTTPMethod.GET,
            {'X-Custom': 'value', 'Content-Type': 'application/json'},
            HTTPStatus.ACCEPTED,
        ),
        (
            HTTPMethod.POST,
            {'X-Custom': 'value', 'Content-Type': 'application/json5'},
            HTTPStatus.CREATED,
        ),
        (
            HTTPMethod.DELETE,
            {'Content-Type': 'application/json'},
            HTTPStatus.OK,
        ),
    ],
)
def test_to_response_correct_validation(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
    headers: dict[str, str],
    status_code: HTTPStatus,
) -> None:
    """Ensures that response headers are validated."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _CorrectToResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content
    assert response.headers == headers
    assert json.loads(response.content) == ['a', 'b']
