from typing import Any

import pytest

from dmr.openapi.mappers.schema_normalization import (
    _dump_value,
    dump_schema,
)
from dmr.openapi.objects import (
    Header,
    OpenAPIType,
    Schema,
)


@pytest.mark.parametrize(
    ('input_value', 'expected_output'),
    [
        # Key normalization:
        (
            Schema(
                type=OpenAPIType.OBJECT,
                max_length=100,
                schema_if=Schema(type=OpenAPIType.STRING),
                external_docs=None,
            ),
            {
                'type': 'object',
                'maxLength': 100,
                'if': {'type': 'string'},
            },
        ),
        # Required field is not dumped:
        (
            Header(description='test', required=False),
            {'description': 'test'},
        ),
    ],
)
def test_dump_schema_no_pydantic(
    *,
    input_value: Any,
    expected_output: Any,
) -> None:
    """Ensure that ``dump_schema`` works without ``pydantic``."""
    assert dump_schema(input_value) == expected_output
    assert _dump_value(input_value) == expected_output
