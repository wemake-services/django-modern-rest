from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _BodyModel(pydantic.BaseModel):
    email: str


@final
class _MyController(Controller[PydanticSerializer], Body[_BodyModel]):
    def post(self) -> str:
        """Simulates `post` method."""
        return self.parsed_body.email


def test_dmr_rf(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that :class:`django_modern_rest.test.DMRRequestFactory` works."""
    request = dmr_rf.post(
        '/whatever/',
        data={'email': 'mail@example.com'},
    )

    assert request.body == b'{"email": "mail@example.com"}'

    response = _MyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.content == b'"mail@example.com"'


def test_dmr_async_rf(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """
    Ensures that :class:`django_modern_rest.test.DMRAsyncRequestFactory` works.

    Fully compatible with ``DMRRequestFactory`` with its API.
    """
    request = dmr_async_rf.post(
        '/whatever/',
        data={'email': 'mail@example.com'},
    )

    assert request.body == b'{"email": "mail@example.com"}'

    response = _MyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response.content == b'"mail@example.com"'
