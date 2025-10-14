import json
from http import HTTPStatus
from typing import final

import pydantic
import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller
from django_modern_rest.exceptions import UnsolvableAnnotationsError
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _MyPydanticModel(pydantic.BaseModel):
    age: int


@final
class _WrongPydanticBodyController(
    Controller[PydanticSerializer],
    Body[_MyPydanticModel],
):
    """All body of these methods are not correct."""

    def post(self) -> str:  # pragma: no cover
        """Does not respect a body type."""
        return 'done'  # not an exception for a better test clarity


def test_invalide_request_body(rf: RequestFactory, faker: Faker) -> None:
    """Ensures that request body validation works for default settings."""
    request = rf.post(
        '/whatever/',
        data={'age': faker.random_int()},  # wrong content-type
    )

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content)['detail'] == snapshot(
        'JSON is malformed: invalid character (byte 1)',
    )


def test_missing_function_return_annotation() -> None:
    """Ensure that they are required."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='return type annotation',
    ):

        class _MissingReturnController(Controller[PydanticSerializer]):
            def get(self):  # type: ignore[no-untyped-def]
                """Does not respect a body type."""
