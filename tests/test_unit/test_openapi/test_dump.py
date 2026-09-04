import json

from dmr.internal.json import json_dump as internal_json_dump
from dmr.internal.json import json_dumps as internal_json_dumps
from dmr.openapi.dump import json_dump, json_dumps


def test_internal_json_dumps() -> None:
    """Ensure internal json_dumps serializes objects to strings."""
    data = {'key': 'value', 'number': 42}
    serialized = internal_json_dumps(data)

    assert isinstance(serialized, str)
    assert json.loads(serialized) == data
    # Verify backwards compatibility alias
    assert internal_json_dump(data) == serialized


def test_openapi_json_dumps() -> None:
    """Ensure openapi json_dumps serializes schema to string."""
    schema = {'openapi': '3.1.0', 'info': {'title': 'Test', 'version': '1.0'}}
    serialized = json_dumps(schema)

    assert isinstance(serialized, str)
    assert json.loads(serialized) == schema
    # Verify backwards compatibility alias
    assert json_dump(schema) == serialized
