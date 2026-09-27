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


def test_deprecated_example_value() -> None:
    """Ensure that the deprecated `value` is still dumped as is."""
    assert dump_schema(Example(value='raw')) == {'value': 'raw'}
