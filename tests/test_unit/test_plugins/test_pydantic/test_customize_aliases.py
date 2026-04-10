import json
from http import HTTPStatus
from typing import Any, ClassVar, final

import pydantic
import pytest
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.plugins.pydantic.serializer import ToJsonKwargs, ToModelKwargs
from dmr.test import DMRRequestFactory


@final
class _BodyModel(pydantic.BaseModel):
    full_name: str = pydantic.Field(alias='fullName')


@final
class _NoAliasPydanticSerializer(PydanticSerializer):
    to_json_kwargs: ClassVar[ToJsonKwargs] = {
        **PydanticSerializer.to_json_kwargs,
        'by_alias': False,
    }
    to_model_kwargs: ClassVar[ToModelKwargs] = {
        'by_alias': False,
        'by_name': True,
    }


@final
class _NoAliasController(
    Controller[_NoAliasPydanticSerializer],
):
    def post(self, parsed_body: Body[_BodyModel]) -> _BodyModel:
        """Will consume and produce regular names."""
        return parsed_body


@pytest.mark.parametrize(
    'serializer',
    [PydanticSerializer, PydanticFastSerializer],
)
def test_default_alias_serialization(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    serializer: type[PydanticSerializer],
) -> None:
    """Ensures by default aliases are working."""

    class _AliasController(Controller[serializer]):  # type: ignore[valid-type]
        def post(self, parsed_body: Body[_BodyModel]) -> _BodyModel:
            return parsed_body

    request_data = {'fullName': faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _AliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == request_data


@pytest.mark.parametrize(
    'serializer',
    [PydanticSerializer, PydanticFastSerializer],
)
def test_default_alias_serialization_by_name(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    serializer: type[PydanticSerializer],
) -> None:
    """Ensures by default names do not work."""

    class _AliasController(Controller[serializer]):  # type: ignore[valid-type]
        def post(self, parsed_body: Body[_BodyModel]) -> _BodyModel:
            raise NotImplementedError

    request_data = {'full_name': faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _AliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content)['detail']


@pytest.mark.parametrize(
    'serializer',
    [PydanticSerializer, PydanticFastSerializer],
)
@pytest.mark.parametrize('field_name', ['fullName', 'full_name'])
def test_by_name_and_by_alias(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    serializer: type[PydanticSerializer],
    field_name: str,
) -> None:
    """Ensures by default aliases are working."""

    class _BothSerializer(serializer):  # type: ignore[valid-type, misc]
        to_model_kwargs: ClassVar[ToModelKwargs] = {
            'by_alias': True,
            'by_name': True,
        }

    class _AliasController(Controller[_BothSerializer]):
        def post(self, parsed_body: Body[_BodyModel]) -> _BodyModel:
            return parsed_body

    request_data = {field_name: faker.name()}

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _AliasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == {
        'fullName': request_data[field_name],
    }


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
class _UnserializableController(Controller[PydanticSerializer]):
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
