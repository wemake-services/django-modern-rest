import dataclasses
import inspect
from typing import Any

import pytest

from dmr.openapi import objects
from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.openapi import OpenAPI


def _extensions() -> dict[str, Any]:
    return {'x-first': 1, 'x-second': {'nested': True}}


@pytest.mark.parametrize(
    'openapi_object',
    [
        OpenAPI(info=objects.Info(title='t', version='1'), openapi='3.1.0'),
        objects.Components(),
        objects.Contact(),
        objects.Discriminator(property_name='kind'),
        objects.Encoding(),
        objects.Example(),
        objects.ExternalDocumentation(url='https://example.com'),
        objects.Header(),
        objects.Info(title='t', version='1'),
        objects.License(name='MIT'),
        objects.Link(),
        objects.MediaType(),
        objects.MediaTypeMetadata(),
        objects.OAuthFlow(),
        objects.OAuthFlows(),
        objects.Operation(),
        objects.Parameter(name='q', param_in='query'),
        objects.ParameterMetadata(),
        objects.PathItem(),
        objects.RequestBody(content={}),
        objects.Response(),
        objects.Schema(),
        objects.SecurityScheme(type='http'),
        objects.Server(url='/'),
        objects.ServerVariable(default='v1'),
        objects.Tag(name='users'),
        objects.XML(),
    ],
)
def test_dump_x_extensions(openapi_object: Any) -> None:
    """Extensions are dumped as top-level ``x-`` keys, always last."""
    dumped = dump_schema(
        dataclasses.replace(openapi_object, x_extensions=_extensions()),
    )

    assert 'x_extensions' not in dumped
    assert 'xExtensions' not in dumped
    assert list(dumped)[-2:] == ['x-first', 'x-second']
    assert dumped['x-first'] == 1
    assert dumped['x-second'] == {'nested': True}


def test_all_objects_support_x_extensions() -> None:
    """Every OpenAPI object supports extensions, except ``Reference``."""
    for _, openapi_object in inspect.getmembers(
        objects,
        dataclasses.is_dataclass,
    ):
        field_names = {
            field.name
            for field in dataclasses.fields(openapi_object)  # pyrefly: ignore[bad-argument-type]
        }
        assert ('x_extensions' in field_names) is (
            openapi_object is not objects.Reference
        ), openapi_object
