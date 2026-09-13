from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import Schema


def test_load_schema_keeps_anchor_comment_and_schema_uri() -> None:
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


def test_load_schema_leaves_absent_keyword_attributes_empty() -> None:
    """A schema without those keywords keeps them unset, not ``''``."""
    loaded = load_schema({'type': 'string'})

    assert isinstance(loaded, Schema)
    assert loaded.anchor is None
    assert loaded.comment is None
    assert loaded.schema_uri is None
