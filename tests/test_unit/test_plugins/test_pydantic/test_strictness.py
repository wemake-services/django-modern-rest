import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.serializer import SerializerContext
from django_modern_rest.test import DMRRequestFactory


@final
class _InputModel(pydantic.BaseModel):
    lax_field: int
    strict_field: int = pydantic.Field(strict=True)


@final
class _DefaultInputController(
    Controller[PydanticSerializer],
    Body[_InputModel],
):
    def post(self) -> _InputModel:
        return self.parsed_body


def test_default_input_strictness_lax(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that default input validation is lax."""
    request_data = {'lax_field': '123', 'strict_field': 123}
    request = dmr_rf.post('/whatever/', data=request_data)
    response = _DefaultInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content)['lax_field'] == 123  # noqa: WPS432


def test_default_input_strictness_respects_strict(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that default input validation respects strict on fields."""
    request_data = {'lax_field': 123, 'strict_field': '123'}
    request = dmr_rf.post('/whatever/', data=request_data)
    response = _DefaultInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    error = json.loads(response.content)
    assert error['detail'][0]['loc'] == ['parsed_body', 'strict_field']


@final
class _OutputModel(pydantic.BaseModel):
    output_value: int


@final
class _DefaultOutputController(Controller[PydanticSerializer]):
    def post(self) -> _OutputModel:
        # Returning a string "123" for an int field.
        # If strict=True (default for output), this should fail.
        # If strict=False, this would coerce to 123.
        return {'output_value': '123'}  # type: ignore[return-value]


def test_default_output_strictness(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that default output validation is strict."""
    request = dmr_rf.post('/whatever/')
    response = _DefaultOutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = json.loads(response.content)
    assert error['detail'][0]['loc'] == ['output_value']
    assert error['detail'][0]['type'] == 'value_error'


@final
class _StrictContext(SerializerContext):
    strict_validation = True


@final
class _ExplicitStrictInputController(
    Controller[PydanticSerializer],
    Body[_InputModel],
):
    serializer_context_cls = _StrictContext

    def post(self) -> _InputModel:
        return self.parsed_body  # pragma: no cover


def test_explicit_input_strictness(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that user can enable strict validation for inputs."""
    request_data = {'lax_field': '123', 'strict_field': 123}
    request = dmr_rf.post('/whatever/', data=request_data)
    response = _ExplicitStrictInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    error = json.loads(response.content)
    assert error['detail'][0]['loc'] == ['parsed_body', 'lax_field']
    assert error['detail'][0]['type'] == 'value_error'
