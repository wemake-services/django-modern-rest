import pytest
from django.conf import LazySettings

from dmr.openapi import (
    OpenAPIConfig,
    OpenAPIContext,
    build_schema,
    default_config,
)
from dmr.openapi.objects import Tag
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
        build_schema(router=Router('', []))


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
    router = Router('', [])
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
    router = Router('', [])
    schema = build_schema(router)

    schema.tags = []
    tag = Tag(name='Whatever')
    schema.tags.append(tag)

    assert schema.tags == [tag]


def test_pass_both_context_and_config() -> None:
    """Ensures that you can't pass both ``config`` and ``context``."""
    router = Router('', [])
    config = default_config()
    context = OpenAPIContext(config)
    with pytest.raises(ValueError, match='Passing both'):
        build_schema(router, context=context, config=config)  # type: ignore[call-overload]
