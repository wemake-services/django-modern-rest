import json
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command


@pytest.mark.parametrize(
    ('kwargs', 'has_indent', 'sort_keys'),
    [
        ({}, False, False),  # default
        ({'format': 'json'}, False, False),  # explicit json
        ({'indent': 2}, True, False),  # pretty
        ({'sort_keys': True}, False, True),  # sort keys
        ({'indent': 2, 'sort_keys': True}, True, True),
    ],
)
def test_export_schema_json(
    kwargs: dict[str, Any],
    *,
    has_indent: bool,
    sort_keys: bool,
) -> None:
    """JSON export variations."""
    out = StringIO()
    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        stdout=out,
        **kwargs,
    )

    output = out.getvalue()
    parsed = json.loads(output)

    if sort_keys:
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    assert ('  ' in output) == has_indent


@pytest.mark.parametrize(
    ('kwargs', 'has_indent', 'sort_keys'),
    [
        ({}, False, False),  # default
        ({'format': 'yaml'}, False, False),  # explicit
        ({'indent': 4}, True, False),  # custom indentation
        ({'sort_keys': True}, False, True),  # sort keys
        ({'indent': 4, 'sort_keys': True}, True, True),
    ],
)
def test_export_schema_yaml(
    kwargs: dict[str, Any],
    *,
    has_indent: bool,
    sort_keys: bool,
) -> None:
    """YAML export validation."""
    yaml = pytest.importorskip('yaml')
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        stdout=out,
        **kwargs,
    )

    output = out.getvalue()
    parsed = yaml.safe_load(output)

    if sort_keys:
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    assert ('    ' in output.split('\n')[1]) == has_indent


@pytest.mark.parametrize(
    ('schema_path', 'expected_exception'),
    [
        ('does.not.exist:schema', ImportError),
        ('server.urls:urlpatterns', AttributeError),
    ],
)
def test_export_schema_invalid_input(
    schema_path: str,
    expected_exception: type[Exception],
) -> None:
    """Invalid schema inputs raise the expected exception."""
    with pytest.raises(expected_exception):
        call_command('dmr_export_schema', schema_path)
