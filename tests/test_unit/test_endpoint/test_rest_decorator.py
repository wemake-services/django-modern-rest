import json
from http import HTTPStatus
from typing import final

from django.http import HttpResponse
from django.test import RequestFactory

from django_modern_rest import Controller, rest
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _CustomStatusCodeController(Controller[PydanticSerializer]):
    """All body of these methods are not correct."""

    @rest(status_code=HTTPStatus.OK)
    def post(self) -> dict[str, str]:
        """Modifies status code from 201 to 200."""
        return {'result': 'done'}


def test_rest_status_code(rf: RequestFactory) -> None:
    """Ensures we can change status code."""
    request = rf.post('/whatever/')

    response = _CustomStatusCodeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'result': 'done'}
