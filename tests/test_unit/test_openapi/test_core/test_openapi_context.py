import pytest

from dmr.openapi import OpenAPIContext, default_config
from dmr.openapi.objects import Schema


def test_register_schema_twice() -> None:
    """Ensures that explicit override is required."""
    context = OpenAPIContext(default_config())
    test_schema = Schema(title='test')

    context.register_schema(int, test_schema)

    with pytest.raises(ValueError, match='is already registered'):
        context.register_schema(int, test_schema)

    context.register_schema(int, test_schema, override=True)
