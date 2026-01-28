from unittest.mock import Mock

from faker import Faker

from django_modern_rest.openapi.converter import (
    normalize_value,
)
from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition


def test_fd_conversion_with_kwarg_def(faker: Faker) -> None:
    """Test FieldDefinition conversion including KwargDefinition."""
    mock_converter = Mock()
    default_val = faker.random_int()
    exclusive_minimum = faker.random_int()

    fd = FieldDefinition(
        name='test',
        extra_data={
            'exclusiveMinimum': exclusive_minimum,
            'examples': [{'key': 'value'}],
        },
        kwarg_definition=KwargDefinition(
            gt=exclusive_minimum,
            title='Test',
            default=default_val,
            schema_extra={'x-custom': 'value'},
        ),
    )

    normalized = normalize_value(fd, mock_converter)

    assert normalized == {
        'exclusiveMinimum': exclusive_minimum,
        'examples': [{'key': 'value'}],
        'title': 'Test',
        'default': default_val,
        'x-custom': 'value',
    }


def test_fd_conversion_defaults() -> None:
    """Test FieldDefinition conversion with default KwargDefinition values."""
    mock_converter = Mock()

    fd = FieldDefinition(
        name='test',
        extra_data={'type': 'string'},
        kwarg_definition=KwargDefinition(title='Test Defaults'),
    )

    normalized = normalize_value(fd, mock_converter)

    assert normalized == {
        'type': 'string',
        'title': 'Test Defaults',
    }


def test_field_definition_conversion_no_kwarg_def() -> None:
    """Test FieldDefinition conversion without KwargDefinition."""
    mock_converter = Mock()

    fd = FieldDefinition(
        name='test',
        extra_data={'type': 'integer'},
        kwarg_definition=None,
    )

    normalized = normalize_value(fd, mock_converter)

    assert normalized == {'type': 'integer'}
