import json
from http import HTTPStatus
from typing import Any, ClassVar, final

import pydantic
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import (
    FromPythonKwargs,
    ModelDumpKwargs,
    PydanticSerializer,
)
from django_modern_rest.test import DMRRequestFactory


@final
class _BodyModel(pydantic.BaseModel):
    full_name: str = pydantic.Field(alias='fullName')


@final
class _AliasController(Controller[PydanticSerializer], Body[_BodyModel]):
    def post(self) -> _BodyModel:
        """Will consume and produce aliased names."""
        return self.parsed_body


@final
class _NoAliasPydanticSerializer(PydanticSerializer):
    model_dump_kwargs: ClassVar[ModelDumpKwargs] = {
        **PydanticSerializer.model_dump_kwargs,
        'by_alias': False,
    }
    from_python_kwargs: ClassVar[FromPythonKwargs] = {
        'by_alias': False,
        'by_name': True,
    }


@final
class _NoAliasController(
    Controller[_NoAliasPydanticSerializer],
    Body[_BodyModel],
):
    def post(self) -> _BodyModel:
        """Will consume and produce regular names."""
        return self.parsed_body


def test_default_alias_serialization(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures by default aliases are working."""
    request_data = {'fullName': faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _AliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == request_data


def test_default_alias_serialization_by_name(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures by default names do not work."""
    request_data = {'full_name': faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _AliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content)['detail']


def test_custom_alias_serialization(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures in custom type names are working."""
    request_data = {'full_name': faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _NoAliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == request_data


def test_custom_alias_serialization_by_alias(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures in custom type aliases do not work."""
    request_data = {'fullName': faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _NoAliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST


@final
class _UnserializableController(Controller[_NoAliasPydanticSerializer]):
    def post(self) -> dict[str, Any]:
        return {'a': object()}


def test_not_serializable_response(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures in custom type aliases do not work."""
    request = dmr_rf.post('/whatever/', data={})

    response = _UnserializableController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })
