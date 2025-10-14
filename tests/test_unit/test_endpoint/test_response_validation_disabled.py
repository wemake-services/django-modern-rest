import json
from collections.abc import Iterator
from http import HTTPMethod, HTTPStatus
from typing import final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from django_modern_rest import Controller, validate
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.settings import (
    DMR_VALIDATE_RESPONSE_KEY,
    resolve_defaults,
    resolve_setting,
)
from django_modern_rest.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _disable_response_validation(settings: LazySettings) -> Iterator[None]:
    # TODO: make a fixture out of it.
    resolve_defaults.cache_clear()
    resolve_setting.cache_clear()

    settings.DMR_SETTINGS = {
        DMR_VALIDATE_RESPONSE_KEY: False,
    }

    yield

    resolve_defaults.cache_clear()
    resolve_setting.cache_clear()


@final
class _MyPydanticModel(pydantic.BaseModel):
    email: str


@final
class _WrongController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct."""

    def get(self) -> _MyPydanticModel:
        """Does not respect an annotation type."""
        return 1  # type: ignore[return-value]

    @validate(return_type=list[int], status_code=HTTPStatus.OK)
    def post(self) -> HttpResponse:
        """Does not respect a `return_type` validator."""
        return HttpResponse(b'1')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
    ],
)
def test_validate_response_disabled(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response validation can be disabled."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == 1


@final
class _WrongStatusCodeController(Controller[PydanticSerializer]):
    @validate(return_type=list[int], status_code=HTTPStatus.CREATED)
    def get(self) -> HttpResponse:
        """Does not respect a `status_code` validator."""
        return HttpResponse(b'[]', status=HTTPStatus.OK)


def test_validate_status_code(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.get('/whatever/')

    response = _WrongStatusCodeController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == []
