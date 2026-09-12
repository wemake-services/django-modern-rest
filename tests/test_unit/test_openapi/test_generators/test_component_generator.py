import re
from typing import Annotated, Any, Generic, TypeAlias, TypeVar

import pytest
from django.urls import path
from typing_extensions import override

from dmr import Controller
from dmr.components import ComponentParser
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.component_parsers import (
    _ConverterSchema,
    _with_converter_schema,
)
from dmr.openapi.objects import Parameter, Reference, Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer

_FakeT = TypeVar('_FakeT')


class _FakeComponent(ComponentParser, Generic[_FakeT]):
    context_name = 'parsed_fake'

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type[BaseSerializer],
        context: OpenAPIContext,
    ) -> Any:
        """Just return None."""


_Fake: TypeAlias = Annotated[_FakeT, _FakeComponent()]


class _FakeController(Controller[PydanticSerializer]):
    def get(self, parsed_fake: _Fake[int]) -> str:
        raise NotImplementedError


def test_fake_component(openapi_context: OpenAPIContext) -> None:
    """Ensures that wrong components raise."""
    with pytest.raises(
        TypeError,
        match=re.escape(
            "Returning <class 'NoneType'> from ComponentParser.get_schema",
        ),
    ):
        openapi_context.generators.component_parsers(
            'unique-operationid',
            path('/', _FakeController.as_view()),
            _FakeController.api_endpoints['GET'].metadata,
            PydanticSerializer,
        )


class _PathController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


def _single_schema(
    path_params: list[Parameter | Reference],
) -> Schema:
    """Return the schema of the only path parameter."""
    assert len(path_params) == 1
    path_param = path_params[0]
    assert isinstance(path_param, Parameter)
    assert isinstance(path_param.schema, Schema)
    return path_param.schema


@pytest.mark.parametrize(
    ('raw_path', 'expected_pattern', 'expected_description'),
    [
        ('tags/<slug:tag>/', r'^(?:[-a-zA-Z0-9_]+)$', None),
        ('files/<path:file_path>/', None, 'Can contain slashes'),
        ('articles/<int:article_id>/', None, None),
        ('users/<uuid:user_id>/', None, None),
        ('plain/<str:name>/', None, None),
        ('bare/<name>/', None, None),
    ],
)
def test_path_converter_schemas(
    openapi_context: OpenAPIContext,
    raw_path: str,
    expected_pattern: str | None,
    expected_description: str | None,
) -> None:
    """Ensure that converters bring their own info into the schema."""
    _request_body, path_params = openapi_context.generators.component_parsers(
        'unique-operationid',
        path(raw_path, _PathController.as_view()),
        _PathController.api_endpoints['GET'].metadata,
        PydanticSerializer,
    )

    assert path_params is not None
    schema = _single_schema(path_params)
    assert schema.pattern == expected_pattern
    assert schema.description == expected_description


def test_reference_keeps_its_schema() -> None:
    """Ensure that we never touch references."""
    reference = Reference(ref='#/components/schemas/User')
    assert _with_converter_schema(reference, {}) is reference


def test_unknown_converter_keeps_param() -> None:
    """Ensure that parameters without a prepared schema stay untouched."""
    path_param = Parameter(name='tag', param_in='path', schema=Schema())
    assert _with_converter_schema(path_param, {}) is path_param


def test_referenced_schema_keeps_param() -> None:
    """Ensure that parameters with referenced schemas stay untouched."""
    path_param = Parameter(
        name='tag',
        param_in='path',
        schema=Reference(ref='#/components/schemas/Tag'),
    )
    prepared = {'tag': _ConverterSchema(pattern='^tag$')}
    assert _with_converter_schema(path_param, prepared) is path_param
