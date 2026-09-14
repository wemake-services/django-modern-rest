from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import (
    XML,
    Reference,
    Discriminator,
    OpenAPIFormat,
    OpenAPIType,
    Schema,
)


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


def test_load_schema_openapi_v32_fields() -> None:
    """Keep the OpenAPI 3.2 additions of ``xml`` and ``discriminator``."""
    loaded = load_schema(
        {
            'type': 'object',
            'xml': {'name': 'pet', 'nodeType': 'element'},
            'discriminator': {
                'propertyName': 'petType',
                'defaultMapping': 'OtherPet',
            },
        },
    )

    assert loaded.xml == XML(name='pet', node_type='element')
    assert loaded.discriminator == Discriminator(
        property_name='petType',
        default_mapping='OtherPet',
    )


def test_load_schema_without_xml_node_type() -> None:
    """Deprecated ``attribute`` and ``wrapped`` are not defaulted anymore."""
    loaded = load_schema({'type': 'string', 'xml': {'attribute': True}})

    # `wrapped` stays unset, it used to be loaded as `False`:
    assert loaded.xml == XML(attribute=True, wrapped=None)


def test_load_schema_format_preserve_type() -> None:
    """Known formats load as enum members, custom ones stay strings."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1489
    known = load_schema({'type': 'string', 'format': 'date'})
    assert known.format is OpenAPIFormat.DATE

    custom = load_schema({'type': 'string', 'format': 'cool-format'})
    assert custom.format == 'cool-format'
    assert not isinstance(custom.format, OpenAPIFormat)


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
