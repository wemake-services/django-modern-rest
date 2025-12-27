import enum
from typing import Any

import pytest

from django_modern_rest.openapi.converter import (
    SchemaConverter,
    normalize_key,
    normalize_value,
)
from django_modern_rest.openapi.objects import (
    OpenAPIFormat,
    OpenAPIType,
    Schema,
    Tag,
)


@pytest.fixture
def converter() -> type[SchemaConverter]:
    """Fixtutre for converter class."""
    return SchemaConverter


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        # Special cases for reserved keywords
        ('ref', '$ref'),
        ('param_in', 'in'),
        # Schema prefix removal
        ('schema_not', 'not'),
        ('schema_all_of', 'allOf'),
        # Snake case to camel case conversion
        ('external_docs', 'externalDocs'),
        ('operation_id', 'operationId'),
        ('content_media_type', 'contentMediaType'),
        ('max_length', 'maxLength'),
        ('read_only', 'readOnly'),
        # Single word keys (no change)
        ('name', 'name'),
        ('type', 'type'),
        # Edge cases
        ('', ''),
        ('a', 'a'),
        ('UPPER_CASE', 'upperCase'),
        ('mixed_Case', 'mixedCase'),
        ('numbers_123', 'numbers123'),
    ],
)
def test_normalize_key(input_key: str, expected_output: str) -> None:
    """Ensure that `_normalize_key` converts field names to OpenAPI keys."""
    assert normalize_key(input_key) == expected_output


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
def test_normalize_value_primitives(
    input_value: Any,
    expected_output: Any,
    *,
    converter: SchemaConverter,
) -> None:
    """Ensure that `_normalize_value` returns primitive values as-is."""
    assert normalize_value(input_value, converter.convert) == expected_output


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
def test_normalize_value_list(
    input_value: Any,
    expected_output: Any,
    *,
    converter: SchemaConverter,
) -> None:
    """Ensure that `_normalize_value` processes list recursively."""
    normalized = normalize_value(input_value, converter.convert)
    assert normalized == expected_output


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        ({}, {}),
        ({'a': 1, 'b': 2}, {'a': 1, 'b': 2}),
        ({_TestEnum.INT_VALUE: _TestEnum.STR_VALUE}, {42: 'first'}),
        ({'key1': None, 'key2': 'value'}, {'key1': None, 'key2': 'value'}),
    ],
)
def test_normalize_value_dict(
    input_value: Any,
    expected_output: Any,
    *,
    converter: SchemaConverter,
) -> None:
    """Ensure that `_normalize_value` processes dict recursively."""
    normalized = normalize_value(input_value, converter.convert)
    assert normalized == expected_output


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        # Basic `BaseObject` with `None` values
        (
            Tag(
                name='test-tag',
                description='Test description',
                external_docs=None,
            ),
            {'name': 'test-tag', 'description': 'Test description'},
        ),
        # `Enum` values conversion
        (
            Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.EMAIL),
            {'type': 'string', 'format': 'email'},
        ),
        # Key normalization (snake_case to camelCase)
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
        # Sequence fields (enum as list)
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
        # Nested BaseObject (all_of with Schema)
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
        # Nested BaseObject (one_of with Schema)
        (
            Schema(
                one_of=[Schema(type=OpenAPIType.INTEGER)],
                type=OpenAPIType.OBJECT,
            ),
            {
                'oneOf': [{'type': 'integer'}],
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
                all_of=[Schema(type=OpenAPIType.OBJECT)],
            ),
            {
                'not': {'type': 'string'},
                'allOf': [{'type': 'object'}],
            },
        ),
    ],
)
def test_normalize_value_base_objects(
    input_value: Any,
    expected_output: Any,
    *,
    converter: SchemaConverter,
) -> None:
    """Ensure that `_normalize_value` calls to_schema() correctly."""
    assert normalize_value(input_value, converter.convert) == expected_output
