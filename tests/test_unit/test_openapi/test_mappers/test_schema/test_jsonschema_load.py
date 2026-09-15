from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import XML, Discriminator, OpenAPIType, Schema


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
