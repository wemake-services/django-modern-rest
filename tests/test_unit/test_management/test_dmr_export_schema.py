import json
from io import StringIO

import pytest
from django.core.management import call_command


def test_export_schema_json_default() -> None:
    """JSON output is produced by default."""
    out = StringIO()

    call_command('dmr_export_schema', 'server.urls:schema', stdout=out)

    output = out.getvalue()
    assert json.loads(output)
    assert '  ' not in output


def test_export_schema_json_explicit() -> None:
    """Exports compact valid JSON."""
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        format='json',
        stdout=out,
    )

    output = out.getvalue()
    assert json.loads(output)
    assert '  ' not in output


def test_export_schema_json_pretty() -> None:
    """Indented JSON output."""
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        indent=2,
        stdout=out,
    )

    output = out.getvalue()
    assert json.loads(output)
    assert '  ' in output


def test_export_schema_json_sort_keys() -> None:
    """JSON with sorted keys."""
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        sort_keys=True,
        stdout=out,
    )

    output = out.getvalue()
    parsed = json.loads(output)

    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_export_schema_json_pretty_sort_keys() -> None:
    """JSON output is pretty-printed and sorted."""
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        indent=2,
        sort_keys=True,
        stdout=out,
    )

    output = out.getvalue()
    parsed = json.loads(output)

    keys = list(parsed.keys())
    assert keys == sorted(keys)

    assert '  ' in output


def test_export_schema_yaml() -> None:
    """Exports valid YAML output."""
    yaml = pytest.importorskip('yaml')
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        format='yaml',
        stdout=out,
    )

    yaml.safe_load(out.getvalue())


def test_export_schema_yaml_sort_keys() -> None:
    """YAML output with sorted keys."""
    yaml = pytest.importorskip('yaml')
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        format='yaml',
        sort_keys=True,
        stdout=out,
    )

    parsed = yaml.safe_load(out.getvalue())

    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_export_schema_yaml_indent() -> None:
    """Indented YAML output."""
    yaml = pytest.importorskip('yaml')
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        format='yaml',
        indent=2,
        stdout=out,
    )

    output = out.getvalue()
    assert yaml.safe_load(output)
    assert '  ' in output


def test_export_schema_yaml_pretty_sort_keys() -> None:
    """Indented and sorted YAML output."""
    yaml = pytest.importorskip('yaml')
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        format='yaml',
        indent=2,
        sort_keys=True,
        stdout=out,
    )

    output = out.getvalue()
    parsed = yaml.safe_load(output)

    keys = list(parsed.keys())
    assert keys == sorted(keys)

    assert '  ' in output


def test_export_schema_invalid_path() -> None:
    """A non-existent import path raises ImportError."""
    with pytest.raises(ImportError):
        call_command('dmr_export_schema', 'does.not.exist:schema')


def test_export_schema_not_openapi_instance() -> None:
    """Passing an object that is not an OpenAPI schema raises AttributeError."""
    with pytest.raises(AttributeError):
        call_command('dmr_export_schema', 'server.urls:urlpatterns')
