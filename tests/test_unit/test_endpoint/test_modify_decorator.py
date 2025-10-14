import json
from http import HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from django_modern_rest import Controller, modify
from django_modern_rest.exceptions import MissingEndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _CustomStatusCodeController(Controller[PydanticSerializer]):
    """Testing the status change."""

    @modify(status_code=HTTPStatus.ACCEPTED)
    def post(self) -> dict[str, str]:
        """Modifies status code from default 201 to custom 202."""
        return {'result': 'done'}


def test_modify_status_code(rf: RequestFactory) -> None:
    """Ensures we can change status code."""
    request = rf.post('/whatever/')

    response = _CustomStatusCodeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.ACCEPTED
    assert json.loads(response.content) == {'result': 'done'}


def test_modify_on_response() -> None:
    """Ensures `@modify` is required for `HttpResponse` returns."""
    with pytest.raises(MissingEndpointMetadataError, match='@modify'):

        class _WrongValidate(Controller[PydanticSerializer]):
            @modify(  # type: ignore[deprecated]
                status_code=HTTPStatus.OK,
            )
            def get(self) -> HttpResponse:
                raise NotImplementedError
