import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from dmr import Controller
from dmr.openapi.objects import Reference, Schema
from dmr.openapi.objects.discriminator import Discriminator
from dmr.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from dmr.openapi.objects.external_documentation import ExternalDocumentation
from dmr.openapi.objects.xml import XML
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _ReturnModel(pydantic.BaseModel):
    full_name: str


@final
class _ForwardRefController(Controller[PydanticSerializer]):
    def get(self) -> '_ReturnModel':
        return _ReturnModel(full_name='Example')


def test_forward_ref_pydantic(dmr_rf: DMRRequestFactory) -> None:
    """Ensures by default forward refs are working."""
    request = dmr_rf.get('/whatever/')

    response = _ForwardRefController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'full_name': 'Example'}


def test_forward_ref_rebuild_context() -> None:
    """Ensures by passing an explicit context works."""
    schema = PydanticSerializer.from_python(
        {'type': 'number'},
        Schema,
        strict=False,
        rebuild_namespace={
            'Schema': Schema,
            'Reference': Reference,
            'Discriminator': Discriminator,
            'ExternalDocumentation': ExternalDocumentation,
            'OpenAPIFormat': OpenAPIFormat,
            'OpenAPIType': OpenAPIType,
            'XML': XML,
        },
    )

    assert isinstance(schema, Schema)
    assert schema.type == OpenAPIType.NUMBER


def test_forward_ref_implicit_context() -> None:
    """Ensures by passing an implicit context works."""
    schema = PydanticSerializer.from_python(
        {'type': 'number'},
        Schema,
        strict=False,
        rebuild_namespace=globals(),  # noqa: WPS421
    )

    assert isinstance(schema, Schema)
    assert schema.type == OpenAPIType.NUMBER
