import enum
from typing import Annotated, Any

import pytest

from dmr.internal.dataclass_aliases import Field
from dmr.openapi.mappers.schema_normalization import (
    _dump_field,
    _dump_value,
    dump_schema,
)
from dmr.openapi.objects import (
    Header,
    OpenAPIFormat,
    OpenAPIType,
    Reference,
    Schema,
    Tag,
)


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        # Snake case to camel case conversion:
        ('external_docs', 'externalDocs'),
        ('operation_id', 'operationId'),
        ('content_media_type', 'contentMediaType'),
        ('max_length', 'maxLength'),
        ('read_only', 'readOnly'),
        # Single word keys (no change):
        ('name', 'name'),
        ('type', 'type'),
        # Edge cases:
        ('', ''),
        ('a', 'a'),
        ('UPPER_CASE', 'upperCase'),
        ('mixed_Case', 'mixedCase'),
        ('numbers_123', 'numbers123'),
    ],
)
def test_dump_field(
    *,
    input_key: str,
    expected_output: str,
) -> None:
    """Ensure that ``dump_field`` converts field names to OpenAPI keys."""
    assert _dump_field(input_key, {}) == expected_output


def test_dump_field_alias() -> None:
    """Ensure that ``dump_field`` converts field names to aliases."""
    assert (
        _dump_field('whatever', Annotated[str, Field(alias='$test')]) == '$test'
    )


class _TestEnum(enum.Enum):
    """Test enum for normalization tests."""

    STR_VALUE = 'first'
    INT_VALUE = 42
    NONE_VALUE = None


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        (None, None),
        (True, True),
        (False, False),
        (0, 0),
        (-1, -1),
        (1.5, 1.5),
        ('', ''),
        ('hello', 'hello'),
        (_TestEnum.STR_VALUE, 'first'),
        (_TestEnum.INT_VALUE, 42),
        (_TestEnum.NONE_VALUE, None),
    ],
)
def test_dump_value_primitives(
    *,
    input_value: Any,
    expected_output: Any,
) -> None:
    """Ensure that ``dump_value`` returns primitive values as-is."""
    assert _dump_value(input_value) == expected_output


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        ([], []),
        ([1, 2, 3], [1, 2, 3]),
        (['a', 'b', 'c'], ['a', 'b', 'c']),
        ([True, False], [True, False]),
        ([None, None], [None, None]),
        ([_TestEnum.STR_VALUE], ['first']),
        ([_TestEnum.STR_VALUE, 'other'], ['first', 'other']),
    ],
)
def test_dump_value_list(
    *,
    input_value: Any,
    expected_output: Any,
) -> None:
    """Ensure that ``dump_value`` processes list recursively."""
    assert _dump_value(input_value) == expected_output


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        ({}, {}),
        ({'a': 1, 'b': 2}, {'a': 1, 'b': 2}),
        ({_TestEnum.INT_VALUE: _TestEnum.STR_VALUE}, {42: 'first'}),
        ({'key1': None, 'key2': 'value'}, {'key1': None, 'key2': 'value'}),
    ],
)
def test_dump_value_dict(
    *,
    input_value: Any,
    expected_output: Any,
) -> None:
    """Ensure that ``dump_value`` processes dict recursively."""
    assert _dump_value(input_value) == expected_output


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        # Basic `dataclass` instance with `None` values:
        (
            Tag(
                name='test-tag',
                description='Test description',
                external_docs=None,
            ),
            {'name': 'test-tag', 'description': 'Test description'},
        ),
        # `Enum` values conversion:
        (
            Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
            {'type': 'string', 'format': 'email'},
        ),
        # Key normalization (snake_case to camelCase):
        (
            Schema(
                type=OpenAPIType.OBJECT,
                max_length=100,
                read_only=True,
                external_docs=None,
            ),
            {
                'type': 'object',
                'maxLength': 100,
                'readOnly': True,
            },
        ),
        # Sequence fields (enum as list):
        (
            Schema(
                type=OpenAPIType.ARRAY,
                enum=['value1', 'value2', 'value3'],
            ),
            {
                'type': 'array',
                'enum': ['value1', 'value2', 'value3'],
            },
        ),
        # Nested `dataclass` instances (all_of with Schema):
        (
            Schema(
                all_of=[Schema(type=OpenAPIType.STRING)],
                type=OpenAPIType.OBJECT,
            ),
            {
                'allOf': [{'type': 'string'}],
                'type': 'object',
            },
        ),
        # Mixed types in enum
        (
            Schema(
                type=OpenAPIType.OBJECT,
                enum=['string1', 42, True, None],
            ),
            {
                'type': 'object',
                'enum': ['string1', 42, True, None],
            },
        ),
        # Special key normalization cases
        (
            Schema(
                schema_not=Schema(type=OpenAPIType.STRING),
                schema_if=Schema(type=OpenAPIType.INTEGER),
                schema_else=Schema(type=OpenAPIType.NUMBER),
                schema_then=Schema(type=OpenAPIType.NULL),
            ),
            {
                'not': {'type': 'string'},
                'if': {'type': 'integer'},
                'else': {'type': 'number'},
                'then': {'type': 'null'},
            },
        ),
        # Generic List<T> base schema:
        (
            Schema(
                type=OpenAPIType.ARRAY,
                defs={
                    'content': Schema(dynamic_anchor='T'),
                },
                items=Schema(dynamic_ref='#T'),
            ),
            {
                'type': 'array',
                '$defs': {
                    'content': {'$dynamicAnchor': 'T'},
                },
                'items': {'$dynamicRef': '#T'},
            },
        ),
        # Concrete List<string> referencing the generic via Reference:
        (
            Schema(
                defs={
                    'string-items': Schema(
                        dynamic_anchor='T',
                        type=OpenAPIType.STRING,
                    ),
                },
                any_of=[Reference(ref='list-of-t')],
            ),
            {
                '$defs': {
                    'string-items': {
                        '$dynamicAnchor': 'T',
                        'type': 'string',
                    },
                },
                'anyOf': [{'$ref': 'list-of-t'}],
            },
        ),
        (
            Header(description='test', required=False),
            {'description': 'test'},
        ),
    ],
)
def test_dump_schema_base_objects(
    *,
    input_value: Any,
    expected_output: Any,
) -> None:
    """Ensure that ``_dump_value`` calls ``dump_schema`` correctly."""
    assert dump_schema(input_value) == expected_output
    assert _dump_value(input_value) == expected_output


def test_dump_path_item_with_additional_operations() -> None:
    """Ensure ``PathItem`` dumps ``additional_operations`` with correct alias."""
    from dmr.openapi.objects import PathItem
    from dmr.openapi.objects.operation import Operation

    op = Operation(
        operation_id='purge_items',
        summary='Purge items',
    )
    path_item = PathItem(
        get=op,
        additional_operations={'PURGE': op},
    )
    dumped = dump_schema(path_item)

    assert 'get' in dumped
    assert 'additionalOperations' in dumped
    assert dumped['additionalOperations'] == {
        'PURGE': {'operationId': 'purge_items', 'summary': 'Purge items', 'deprecated': False},
    }


def test_dump_path_item_without_additional_operations() -> None:
    """Ensure ``PathItem`` omits ``additional_operations`` when empty."""
    from dmr.openapi.objects import PathItem
    from dmr.openapi.objects.operation import Operation

    op = Operation(operation_id='get_items')
    path_item = PathItem(get=op)
    dumped = dump_schema(path_item)

    assert 'get' in dumped
    assert 'additionalOperations' not in dumped
