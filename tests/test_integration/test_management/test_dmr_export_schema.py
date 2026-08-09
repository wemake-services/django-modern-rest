import json
from io import StringIO
from typing import Any, Final

import pytest
from django.core.management import call_command

from dmr.management.commands import dmr_export_schema

# From the OpenAPI description:
_NON_ASCII_TEXT: Final = 'Не АСКИИ текст'  # noqa: RUF001


@pytest.mark.parametrize(
    'kwargs',
    [
        {},  # default
        {'format': 'json'},  # explicit json
        {'format': 'json', 'no_ensure_ascii': True},
        {'indent': 0},
        {'indent': None},
        {'indent': 2},  # pretty
        {'sort_keys': True},  # sort keys
        {'indent': 2, 'sort_keys': True},
        {'indent': 2, 'sort_keys': True, 'no_ensure_ascii': True},
    ],
)
def test_export_schema_json(
    *,
    kwargs: dict[str, Any],
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

    if kwargs.get('sort_keys'):
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    assert ('  ' in output) is bool(kwargs.get('indent'))

    if kwargs.get('no_ensure_ascii'):
        assert _NON_ASCII_TEXT in output
    else:
        assert _NON_ASCII_TEXT not in output


@pytest.mark.parametrize(
    'kwargs',
    [
        {},  # default
        {'no_ensure_ascii': True},
        {'indent': 4},  # custom indentation
        {'indent': 2},
        {'indent': None},
        {'sort_keys': True},  # sort keys
        {'indent': 4, 'sort_keys': True},
        {'indent': 4, 'no_ensure_ascii': True},
    ],
)
@pytest.mark.parametrize(
    'export_format',
    [
        # Since all json is a valid yaml, we also include `yaml` / `json` test:
        'yaml',
        'json',
    ],
)
def test_export_schema_yaml(
    *,
    kwargs: dict[str, Any],
    export_format: str,
) -> None:
    """YAML export validation."""
    yaml = pytest.importorskip('yaml')
    out = StringIO()

    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        stdout=out,
        **{**kwargs, 'format': export_format},
    )

    output = out.getvalue()
    assert yaml.safe_load(output)


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


@pytest.mark.parametrize(
    ('kwargs', 'expected_skip_validation'),
    [
        ({}, False),
        ({'skip_validation': True}, True),
    ],
)
def test_export_schema_passes_skip_validation_to_schema_converter(
    *,
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, Any],
    expected_skip_validation: bool,
) -> None:
    """Pass the skip-validation flag to the schema converter.

    This also verifies that the default remains false.
    """
    observed: list[bool] = []

    class FakeSchema:
        def convert(self, *, skip_validation: bool) -> dict[str, bool]:
            observed.append(skip_validation)
            return {'skip_validation': skip_validation}

    monkeypatch.setattr(
        dmr_export_schema,
        'import_string',
        lambda _: FakeSchema(),
    )

    out = StringIO()
    call_command(
        'dmr_export_schema',
        'server.urls:schema',
        stdout=out,
        **kwargs,
    )

    assert observed == [expected_skip_validation]
    assert json.loads(out.getvalue()) == {
        'skip_validation': expected_skip_validation,
    }
