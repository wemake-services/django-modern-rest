import pytest
from django.conf import LazySettings
from inline_snapshot import snapshot

from dmr.openapi import (
    OpenAPIConfig,
    OpenAPIContext,
    build_schema,
    default_config,
)
from dmr.openapi.objects import (
    Components,
    Example,
    Header,
    OpenAPIType,
    Schema,
    Tag,
)
from dmr.routing import Router


def test_config_raises_wrong_type(
    settings: LazySettings,
) -> None:
    """Ensure that ``TypeError`` raised with wrong config type."""
    settings.DMR_SETTINGS = {'openapi_config': 'not-an-object'}

    with pytest.raises(
        TypeError,
        match='OpenAPI config is not set',
    ):
        build_schema(router=Router(''))


def test_schema_nested_objects_can_be_mutated(
    settings: LazySettings,
) -> None:
    """Ensure schema nested objects can be modified in place."""
    settings.DMR_SETTINGS = {
        'openapi_config': OpenAPIConfig(
            title='Original',
            version='1.0.0',
        ),
    }
    router = Router('')
    schema = build_schema(router)

    schema.info.title = 'Modified'

    assert schema.info.title == 'Modified'


def test_schema_collections_can_be_mutated(
    settings: LazySettings,
) -> None:
    """Ensure schema collections can be modified in place."""
    settings.DMR_SETTINGS = {
        'openapi_config': OpenAPIConfig(
            title='Original',
            version='1.0.0',
        ),
    }
    router = Router('')
    schema = build_schema(router)

    schema.tags = []
    tag = Tag(name='Whatever')
    schema.tags.append(tag)

    assert schema.tags == [tag]


def test_pass_both_context_and_config() -> None:
    """Ensures that you can't pass both ``config`` and ``context``."""
    router = Router('')
    config = default_config()
    context = OpenAPIContext(config)
    with pytest.raises(ValueError, match='Passing both'):
        build_schema(router, context=context, config=config)  # type: ignore[call-overload]


def test_multiple_components() -> None:  # noqa: WPS210
    """Ensures that passing multiple components merges correctly."""
    components_one = Components(
        headers={
            'one': Header(
                description='First',
                schema=Schema(type=OpenAPIType.STRING),
            ),
        },
        schemas={'test': Schema(type=OpenAPIType.STRING)},
    )
    components_two = Components(
        headers={
            'two': Header(
                description='Second',
                schema=Schema(type=OpenAPIType.STRING),
            ),
        },
    )
    components_three = Components(
        examples={'example-one': Example(summary='an example')},
    )
    config = OpenAPIConfig(
        title='my title',
        version='1.0.0',
        components=[components_one, components_two, components_three],
    )
    router = Router('')

    schema = build_schema(router, config=config)

    assert schema.convert()['components'] == snapshot({
        'schemas': {'test': {'type': 'string'}},
        'examples': {'example-one': {'summary': 'an example'}},
        'headers': {
            'one': {'schema': {'type': 'string'}, 'description': 'First'},
            'two': {'schema': {'type': 'string'}, 'description': 'Second'},
        },
    })


def test_multiple_components_conflict() -> None:
    """Ensures that passing multiple components conflicts loudly."""
    components_one = Components(
        schemas={'test': Schema(type=OpenAPIType.STRING)},
    )
    components_two = Components(
        schemas={'test': Schema(type=OpenAPIType.STRING)},
    )
    config = OpenAPIConfig(
        title='my title',
        version='1.0.0',
        components=[components_one, components_two],
    )
    router = Router('')

    with pytest.raises(ValueError, match=r"with shared keys: \{'test'\}"):
        build_schema(router, config=config)
