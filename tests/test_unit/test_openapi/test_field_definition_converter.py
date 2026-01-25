from unittest.mock import Mock

from django_modern_rest.openapi.converter import (
    normalize_value,
)
from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition


def test_field_definition_conversion() -> None:
    """Test FieldDefinition conversion using extra_data."""
    mock_converter = Mock()

    fd = FieldDefinition(
        name='test',
        extra_data={
            'exclusiveMinimum': 5,
            'examples': [{'key': 'value'}],
        },
        # Verify KwargDefinition can be passed
        # (currently unused by converter logic)
        kwarg_definition=KwargDefinition(gt=5, title='Test'),
    )

    normalized = normalize_value(fd, mock_converter)

    # Current implementation only converts extra_data
    assert normalized == {
        'exclusiveMinimum': 5,
        'examples': [{'key': 'value'}],
    }
