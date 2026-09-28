from inline_snapshot import snapshot

from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.objects import (
    XML,
    Discriminator,
    OpenAPIFormat,
    OpenAPIType,
    Schema,
)
from dmr.types import EMPTY


def test_load_schema_issue1491() -> None:
    """Keep the schema keywords that sit next to ``$ref``."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1491
    loaded = load_schema(
        {
            '$ref': '#/components/schemas/Address',
            'default': {'city': 'Moscow'},
            'description': 'Where the user lives',
        },
    )

    assert isinstance(loaded, Schema)
    assert loaded == snapshot(
        Schema(
            description='Where the user lives',
            default={'city': 'Moscow'},
            ref='#/components/schemas/Address',
        ),
    )


def test_load_schema_pure_ref() -> None:
    """A ``$ref`` alone is a schema keyword, not a ``Reference``."""
    loaded = load_schema({'$ref': '#/components/schemas/Address'})

    assert loaded == Schema(ref='#/components/schemas/Address')


def test_load_schema_extensions() -> None:
    """Specification extensions, like ``x-thing``, are kept as they are."""
    loaded = load_schema(
        {
            '$ref': '#/components/schemas/Address',
            'x-display-name': 'Home address',
        },
    )
    assert loaded == snapshot(
        Schema(
            ref='#/components/schemas/Address',
            extensions={'x-display-name': 'Home address'},
        ),
    )

    loaded = load_schema({'type': 'string', 'x-range': {'min': 0}})
    assert loaded == snapshot(
        Schema(type=OpenAPIType.STRING, extensions={'x-range': {'min': 0}}),
    )

    loaded = load_schema({'type': 'string'})
    assert loaded == snapshot(Schema(type=OpenAPIType.STRING))


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
    assert loaded == snapshot(
        Schema(
            type=OpenAPIType.STRING,
            anchor='tagged',
            comment='kept for the next reader',
            schema_uri='https://json-schema.org/draft/2020-12/schema',
        ),
    )


def test_load_schema() -> None:
    """A schema without those keywords keeps them unset, not ``''``."""
    loaded = load_schema({'type': 'string'})

    assert isinstance(loaded, Schema)
    assert loaded == Schema(type=OpenAPIType.STRING)


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

    assert loaded == snapshot(
        Schema(
            type=OpenAPIType.OBJECT,
            discriminator=Discriminator(
                property_name='petType',
                default_mapping='OtherPet',
            ),
            xml=XML(name='pet', node_type='element'),
        ),
    )


def test_load_schema_without_xml_node_type() -> None:
    """Deprecated ``attribute`` and ``wrapped`` are not defaulted anymore."""
    loaded = load_schema({'type': 'string', 'xml': {'attribute': True}})

    assert loaded == snapshot(
        Schema(type=OpenAPIType.STRING, xml=XML(attribute=True)),
    )


def test_load_schema_format_preserve_type() -> None:
    """Known formats load as enum members, custom ones stay strings."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1489
    loaded = load_schema({'type': 'string', 'format': 'date'})
    assert loaded == snapshot(
        Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE),
    )

    loaded = load_schema({'type': 'string', 'format': 'cool-format'})
    assert loaded == snapshot(
        Schema(type=OpenAPIType.STRING, format='cool-format'),
    )
    assert loaded.format == 'cool-format'
    assert not isinstance(loaded.format, OpenAPIFormat)


def test_load_schema_none_values() -> None:
    """Keep ``None`` values of ``const``, ``default``, and ``example``."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1619
    loaded = load_schema({'const': None, 'default': None, 'example': None})

    assert loaded.const is None
    assert loaded.default is None
    assert loaded.example is None


def test_load_schema_unset_values() -> None:
    """Missing ``const``, ``default``, and ``example`` are ``EMPTY``."""
    loaded = load_schema({'type': 'string'})

    assert loaded.const is EMPTY
    assert loaded.default is EMPTY
    assert loaded.example is EMPTY
