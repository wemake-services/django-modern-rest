from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import OpenAPIType, Reference, Schema


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


def test_load_schema_ref_with_siblings() -> None:
    """A ``$ref`` with sibling keywords keeps them, they are not lost."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1491
    loaded = load_schema(
        {
            'type': 'object',
            'properties': {
                'address': {
                    '$ref': '#/components/schemas/Address',
                    'default': {'city': 'Moscow'},
                    'description': 'Where the user lives',
                },
            },
        },
    )

    address = loaded.properties['address']  # type: ignore[index]
    assert isinstance(address, Schema)
    assert address.ref == '#/components/schemas/Address'
    # These are `Schema` attributes, they used to be dropped:
    assert address.default == {'city': 'Moscow'}
    assert address.description == 'Where the user lives'


def test_load_schema_ref_in_items() -> None:
    """Sibling keywords are kept in nested schema positions as well."""
    loaded = load_schema(
        {
            'type': 'array',
            'items': {
                '$ref': '#/components/schemas/Address',
                'default': {'city': 'Moscow'},
            },
        },
    )

    schema_items = loaded.items
    assert isinstance(schema_items, Schema)
    assert schema_items.ref == '#/components/schemas/Address'
    assert schema_items.default == {'city': 'Moscow'}


def test_load_schema_plain_reference() -> None:
    """A ``$ref`` without siblings is still a plain reference object."""
    loaded = load_schema(
        {
            'type': 'object',
            'properties': {
                'address': {'$ref': '#/components/schemas/Address'},
            },
        },
    )

    assert isinstance(loaded.properties['address'], Reference)  # type: ignore[index]
