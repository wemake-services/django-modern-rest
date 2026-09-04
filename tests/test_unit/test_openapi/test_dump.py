import json

from dmr.internal.json import json_dump as internal_json_dump
from dmr.internal.json import json_dumps as internal_json_dumps
from dmr.openapi.dump import json_dump, json_dumps


def test_internal_json_dumps() -> None:
    """Ensure internal json_dumps serializes objects to strings."""
    data = {'key': 'value', 'number': 42}
    result = internal_json_dumps(data)

    assert isinstance(result, str)
    assert json.loads(result) == data
    # Verify backwards compatibility alias
    assert internal_json_dump(data) == result


def test_openapi_json_dumps() -> None:
    """Ensure openapi json_dumps serializes schema to string."""
    schema = {'openapi': '3.1.0', 'info': {'title': 'Test', 'version': '1.0'}}
    result = json_dumps(schema)  # type: ignore[arg-type]

    assert isinstance(result, str)
    assert json.loads(result) == schema
    # Verify backwards compatibility alias
    assert json_dump(schema) == result  # type: ignore[arg-type]
