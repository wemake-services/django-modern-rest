import pytest

from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.objects import Example


def test_example_with_both_forms() -> None:
    """Ensure that 3.2 data and serialized examples can be used together."""
    example = Example(
        summary='Both forms',
        data_value={'key': 'value'},
        serialized_value='key=value',
    )

    assert dump_schema(example) == {
        'summary': 'Both forms',
        'dataValue': {'key': 'value'},
        'serializedValue': 'key=value',
    }


@pytest.mark.parametrize(
    'extra_field',
    [
        {'data_value': {'key': 'value'}},
        {'serialized_value': 'key=value'},
        {'external_value': 'https://example.com/example.json'},
    ],
)
def test_deprecated_value_is_exclusive(extra_field: dict[str, object]) -> None:
    """Ensure that deprecated `value` cannot be mixed with the new fields."""
    with pytest.raises(ValueError, match='Both `value` and `data_value`'):
        Example(value='raw', **extra_field)  # type: ignore[arg-type]


def test_serialized_and_external_are_exclusive() -> None:
    """Ensure that a serialized example cannot also be an external one."""
    with pytest.raises(ValueError, match='`serialized_value`'):
        Example(
            serialized_value='key=value',
            external_value='https://example.com/example.json',
        )
