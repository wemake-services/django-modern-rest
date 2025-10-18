import pytest

from django_modern_rest.openapi.objects.base import _normalize_key


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        # Special cases for reserved keywords
        ('ref', '$ref'),
        ('param_in', 'in'),
        # Schema prefix removal (different patterns)
        ('schema_not', 'not'),
        ('schema_all_of', 'allOf'),
        # Snake case to camel case conversion (different patterns)
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
    assert _normalize_key(input_key) == expected_output
