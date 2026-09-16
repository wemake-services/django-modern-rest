from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import OpenAPIFormat, OpenAPIType, Schema


def test_load_schema_issue1490() -> None:
    """Keep ``$anchor``, ``$comment`` and ``$schema`` on the schema."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1490
    loaded = load_schema(
        {
            'type': 'string',
            '$anchor': 'tagged',
            '$comment': 'kept for the next reader',
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
        },
    )

    assert isinstance(loaded, Schema)
    assert loaded.anchor == 'tagged'
    assert loaded.comment == 'kept for the next reader'
    assert loaded.schema_uri == 'https://json-schema.org/draft/2020-12/schema'


def test_load_schema() -> None:
    """A schema without those keywords keeps them unset, not ``''``."""
    loaded = load_schema({'type': 'string'})

    assert isinstance(loaded, Schema)
    assert loaded == Schema(type=OpenAPIType.STRING)
    assert loaded.anchor is None
    assert loaded.comment is None
    assert loaded.schema_uri is None


def test_load_schema_format_preserve_type() -> None:
    """Known formats load as enum members, custom ones stay strings."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1489
    known = load_schema({'type': 'string', 'format': 'date'})
    assert known.format is OpenAPIFormat.DATE

    custom = load_schema({'type': 'string', 'format': 'cool-format'})
    assert custom.format == 'cool-format'
    assert not isinstance(custom.format, OpenAPIFormat)
