import json
from http import HTTPMethod, HTTPStatus

import pytest
from django.http import HttpResponse

from django_modern_rest import (
    Controller,
    HeaderDescription,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _ToResponseController(Controller[PydanticSerializer]):
    @validate(
        return_type=list[str],
        status_code=HTTPStatus.ACCEPTED,
        headers={'X-Custom': HeaderDescription()},
    )
    def get(self) -> HttpResponse:
        """Tests that `.to_response` works correctly."""
        return self.to_response(
            ['a', 'b'],
            headers={'X-Custom': 'value'},
            status_code=HTTPStatus.ACCEPTED,
        )

    @validate(
        return_type=list[str],
        status_code=HTTPStatus.ACCEPTED,
        headers={'X-Custom': HeaderDescription()},
    )
    def post(self) -> HttpResponse:
        """Wrong body format."""
        return self.to_response(
            [1, 2],
            headers={'X-Custom': 'value'},
            status_code=HTTPStatus.ACCEPTED,
        )

    @validate(
        return_type=list[str],
        status_code=HTTPStatus.ACCEPTED,
        headers={'X-Custom': HeaderDescription()},
    )
    def put(self) -> HttpResponse:
        """Wrong headers."""
        return self.to_response(
            ['a', 'b'],
            status_code=HTTPStatus.ACCEPTED,
        )

    @validate(
        return_type=list[str],
        status_code=HTTPStatus.ACCEPTED,
        headers={'X-Custom': HeaderDescription()},
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

    response = _ToResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_to_response_correct_validation(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response headers are validated."""
    request = dmr_rf.get('/whatever/')

    response = _ToResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.headers == {
        'X-Custom': 'value',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == ['a', 'b']
