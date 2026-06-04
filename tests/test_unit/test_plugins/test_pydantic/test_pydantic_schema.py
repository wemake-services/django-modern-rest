# NOTE: when editing this file, also edit `test_msgspec_schema.py`

import enum
from collections.abc import Iterable, Mapping
from typing import Annotated, Any, Literal, Optional, Union

import pydantic
import pytest
from typing_extensions import TypedDict

from dmr import Controller, Cookies, Headers, Path, Query
from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi import build_schema
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators import SchemaGenerator
from dmr.openapi.objects import OpenAPIFormat, OpenAPIType, Reference, Schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


@pytest.fixture
def schema_generator(openapi_context: OpenAPIContext) -> SchemaGenerator:
    """Fixture for ``SchemaGenerator`` class."""
    return openapi_context.generators.schema


@pytest.mark.parametrize(
    ('source_type', 'schema_type'),
    [
        (int, OpenAPIType.INTEGER),
        (float, OpenAPIType.NUMBER),
        (str, OpenAPIType.STRING),
        (bytes, OpenAPIType.STRING),
        (bool, OpenAPIType.BOOLEAN),
        (None, OpenAPIType.NULL),
    ],
)
def test_simple_types(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    schema_type: OpenAPIType,
) -> None:
    """Ensure schema is generated correctly for simple types."""
    schema = schema_generator(source_type, PydanticSerializer)

    assert isinstance(schema, Schema)
    assert schema.type == schema_type, source_type


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            list[int],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            list,
            Schema(type=OpenAPIType.ARRAY, items=Schema()),
        ),
        (
            set[float],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.NUMBER),
                unique_items=True,
            ),
        ),
        (
            frozenset[str],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.STRING),
                unique_items=True,
            ),
        ),
        (
            Iterable[str],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.STRING),
            ),
        ),
        # `Collection[T]` is not supported by `pydantic`
        (
            tuple[bool, ...],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.BOOLEAN),
            ),
        ),
        (
            tuple[int, str],
            Schema(
                type=OpenAPIType.ARRAY,
                items=None,
                max_items=2,
                min_items=2,
                prefix_items=[
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.STRING),
                ],
            ),
        ),
        (
            tuple[()],
            Schema(
                type=OpenAPIType.ARRAY,
                items=None,
                max_items=0,
                min_items=0,
            ),
        ),
        (
            dict[str, int],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            dict[str, Any],
            Schema(type=OpenAPIType.OBJECT, additional_properties=True),
        ),
        (
            dict,
            Schema(type=OpenAPIType.OBJECT, additional_properties=True),
        ),
        (
            Mapping[str, float],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.NUMBER),
            ),
        ),
    ],
)
def test_generic_objects(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for generic objects."""
    schema = schema_generator(source_type, PydanticSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Optional[None],  # noqa: UP045
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Optional[int],  # noqa: UP045
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.NULL),
                ],
            ),
        ),
        (
            Union[None, None],  # noqa: UP007
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Union[str, int, None],  # noqa: UP007
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.STRING),
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.NULL),
                ],
            ),
        ),
        (
            bool | float,
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.BOOLEAN),
                    Schema(type=OpenAPIType.NUMBER),
                ],
            ),
        ),
    ],
)
def test_union_schema(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for generic objects."""
    schema = schema_generator(source_type, PydanticSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Annotated[dict[str, int], 'meta'],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            Annotated[str, 'meta'],
            Schema(type=OpenAPIType.STRING),
        ),
        (
            Annotated[str | int, 'meta'],
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.STRING),
                    Schema(type=OpenAPIType.INTEGER),
                ],
            ),
        ),
    ],
)
def test_annotated_objects(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for annotated."""
    schema = schema_generator(source_type, PydanticSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


class _TestEnum(enum.IntEnum):
    height = 1
    width = 2


def test_enum(
    schema_generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure schema for enums is correct."""
    reference = schema_generator(_TestEnum, PydanticSerializer)
    assert isinstance(reference, Reference)

    schema = openapi_context.registries.schema.maybe_resolve_reference(
        reference,
    )
    assert schema == Schema(
        type=OpenAPIType.INTEGER,
        enum=[1, 2],
        title=_TestEnum.__qualname__,
    )


def _assert_enum_parameter_schema(
    *,
    controller: type[Controller[PydanticSerializer]],
    component_name: str,
    expected_schema: dict[str, Any],
) -> None:
    """Ensure enum parameter fields register referenced schemas."""
    schema = build_schema(
        Router(
            'api/',
            [path('test/<str:enum_value>/', controller.as_view(), name='test')],
        ),
    ).convert()

    operation = schema['paths']['/api/test/{enum_value}/']['get']
    parameter_specs = {
        (parameter['name'], parameter['in']): parameter
        for parameter in operation['parameters']
    }

    for parameter_location in ('path', 'query', 'header', 'cookie'):
        parameter = parameter_specs['enum_value', parameter_location]
        assert parameter['schema'] == {
            '$ref': f'#/components/schemas/{component_name}',
        }
    assert schema['components']['schemas'][component_name] == expected_schema


def test_parameter_schema_with_enum() -> None:
    """Ensure enum parameter fields register referenced schemas."""

    class _QueryEnum(enum.Enum):
        alpha = 'alpha'
        beta = 'beta'

    class _EnumPath(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumQuery(pydantic.BaseModel):
        enum_value: _QueryEnum = _QueryEnum.alpha

    class _EnumHeaders(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumCookies(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumQueryController(Controller[PydanticSerializer]):
        async def get(
            self,
            parsed_path: Path[_EnumPath],
            parsed_query: Query[_EnumQuery],
            parsed_headers: Headers[_EnumHeaders],
            parsed_cookies: Cookies[_EnumCookies],
        ) -> None:
            raise NotImplementedError

    _assert_enum_parameter_schema(
        controller=_EnumQueryController,
        component_name=_QueryEnum.__name__,
        expected_schema={
            'enum': ['alpha', 'beta'],
            'title': _QueryEnum.__name__,
            'type': 'string',
        },
    )


def test_parameter_schema_with_int_enum() -> None:
    """Ensure int enum parameter fields register referenced schemas."""

    class _QueryEnum(enum.IntEnum):
        alpha = 1
        beta = 2

    class _EnumPath(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumQuery(pydantic.BaseModel):
        enum_value: _QueryEnum = _QueryEnum.alpha

    class _EnumHeaders(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumCookies(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumQueryController(Controller[PydanticSerializer]):
        async def get(
            self,
            parsed_path: Path[_EnumPath],
            parsed_query: Query[_EnumQuery],
            parsed_headers: Headers[_EnumHeaders],
            parsed_cookies: Cookies[_EnumCookies],
        ) -> None:
            raise NotImplementedError

    _assert_enum_parameter_schema(
        controller=_EnumQueryController,
        component_name=_QueryEnum.__name__,
        expected_schema={
            'enum': [1, 2],
            'title': _QueryEnum.__name__,
            'type': 'integer',
        },
    )


def test_parameter_schema_with_str_enum() -> None:
    """Ensure str enum parameter fields register referenced schemas."""

    class _QueryEnum(enum.StrEnum):
        alpha = 'alpha'
        beta = 'beta'

    class _EnumPath(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumQuery(pydantic.BaseModel):
        enum_value: _QueryEnum = _QueryEnum.alpha

    class _EnumHeaders(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumCookies(pydantic.BaseModel):
        enum_value: _QueryEnum

    class _EnumQueryController(Controller[PydanticSerializer]):
        async def get(
            self,
            parsed_path: Path[_EnumPath],
            parsed_query: Query[_EnumQuery],
            parsed_headers: Headers[_EnumHeaders],
            parsed_cookies: Cookies[_EnumCookies],
        ) -> None:
            raise NotImplementedError

    _assert_enum_parameter_schema(
        controller=_EnumQueryController,
        component_name=_QueryEnum.__name__,
        expected_schema={
            'enum': ['alpha', 'beta'],
            'title': _QueryEnum.__name__,
            'type': 'string',
        },
    )


def test_root_model(
    schema_generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure schema for enums is correct."""
    reference = schema_generator(
        pydantic.RootModel[list[int]],
        PydanticSerializer,
    )
    assert isinstance(reference, Reference)

    schema = openapi_context.registries.schema.maybe_resolve_reference(
        reference,
    )
    assert schema == Schema(
        type=OpenAPIType.ARRAY,
        items=Schema(type=OpenAPIType.INTEGER),
        title='RootModel[list[int]]',
    )


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Literal[1, 2],
            Schema(enum=[1, 2], type=OpenAPIType.INTEGER),
        ),
        (
            Literal[1, 'a', None, True],
            Schema(enum=[1, 'a', None, True]),
        ),
    ],
)
def test_literal_types(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for literal types."""
    schema = schema_generator(source_type, PydanticSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


class _TestTypedDict(TypedDict):
    attr: int
    specific_field: pydantic.AnyHttpUrl


def test_type_mapper_typeddict(
    schema_generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that schema for ``TypedDict`` returns ``None``."""
    reference = schema_generator(_TestTypedDict, PydanticSerializer)
    assert isinstance(reference, Reference)

    schema = openapi_context.registries.schema.maybe_resolve_reference(
        reference,
    )
    assert schema == Schema(
        type=OpenAPIType.OBJECT,
        title=_TestTypedDict.__qualname__,
        required=['attr', 'specific_field'],
        properties={
            'attr': Schema(type=OpenAPIType.INTEGER, title='Attr'),
            'specific_field': Schema(
                type=OpenAPIType.STRING,
                min_length=1,
                format=OpenAPIFormat.URI,
                title='Specific Field',
            ),
        },
    )


class _TestClass:
    attr: int


def test_unsupported_type(schema_generator: SchemaGenerator) -> None:
    """Ensures that unsupported types raise."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='Cannot generate OpenAPI schema',
    ):
        schema_generator(_TestClass, PydanticSerializer)
