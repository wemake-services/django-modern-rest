from typing import Any

import pytest

from dmr.openapi.mappers.schema_normalization import (
    _load_field,
    _normalize_key,
    load_schema,
)
from dmr.openapi.objects import (
    OpenAPIType,
    PathItem,
    Reference,
    Schema,
)
from dmr.plugins.pydantic.serializer import PydanticSerializer


# ==============================================================================
# _load_field
# ==============================================================================


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        # camelCase → snake_case (non-aliased fields):
        ('allOf', 'all_of'),
        ('anyOf', 'any_of'),
        ('oneOf', 'one_of'),
        ('maxLength', 'max_length'),
        ('minLength', 'min_length'),
        ('maxItems', 'max_items'),
        ('minItems', 'min_items'),
        ('additionalProperties', 'additional_properties'),
        ('contentMediaType', 'content_media_type'),
        ('operationId', 'operation_id'),
        ('readOnly', 'read_only'),
        # Alias fields — returned as-is so pydantic can match them:
        ('$ref', '$ref'),
        ('not', 'not'),
        ('if', 'if'),
        ('then', 'then'),
        ('else', 'else'),
        # Lowercase non-aliased fields (no change needed):
        ('type', 'type'),
        ('title', 'title'),
        ('description', 'description'),
        ('format', 'format'),
    ],
)
def test_load_field_schema(
    *,
    input_key: str,
    expected_output: str,
) -> None:
    """Ensure ``_load_field`` converts OpenAPI keys for pydantic/Schema."""
    assert _load_field(input_key, Schema) == expected_output


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        ('$ref', '$ref'),
        ('summary', 'summary'),
        ('description', 'description'),
        ('operationId', 'operation_id'),
    ],
)
def test_load_field_path_item(
    *,
    input_key: str,
    expected_output: str,
) -> None:
    """Ensure ``_load_field`` handles PathItem keys correctly."""
    assert _load_field(input_key, PathItem) == expected_output


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        # Special $ aliases:
        ('$defs', '$defs'),
        ('$dynamicRef', '$dynamicRef'),
        ('$dynamicAnchor', '$dynamicAnchor'),
    ],
)
def test_load_field_dollar_aliases(
    *,
    input_key: str,
    expected_output: str,
) -> None:
    """Ensure ``_load_field`` keeps ``$``-prefixed aliases unchanged."""
    assert _load_field(input_key, Schema) == expected_output


# ==============================================================================
# _normalize_key
# ==============================================================================


@pytest.mark.parametrize(
    ('input_key', 'expected_output'),
    [
        # camelCase → snake_case:
        ('allOf', 'all_of'),
        ('maxLength', 'max_length'),
        ('readOnly', 'read_only'),
        ('operationId', 'operation_id'),
        # $-prefixed keys are preserved (pydantic uses them as aliases):
        ('$ref', '$ref'),
        ('$defs', '$defs'),
        ('$dynamicRef', '$dynamicRef'),
        ('$dynamicAnchor', '$dynamicAnchor'),
        # Aliases without $ are already lowercase (unchanged):
        ('not', 'not'),
        ('if', 'if'),
        # Plain lowercase:
        ('type', 'type'),
        ('format', 'format'),
    ],
)
def test_normalize_key(
    *,
    input_key: str,
    expected_output: str,
) -> None:
    """Ensure ``_normalize_key`` converts nested dict keys correctly."""
    assert _normalize_key(input_key) == expected_output


# ==============================================================================
# load_schema — Schema
# ==============================================================================


def test_load_schema_simple_type() -> None:
    """Load a simple ``type`` field into Schema."""
    result = load_schema({'type': 'string'}, Schema, PydanticSerializer)

    assert isinstance(result, Schema)
    assert result.type == OpenAPIType.STRING


def test_load_schema_camel_case_fields() -> None:
    """Load camelCase fields (maxLength, readOnly) into Schema."""
    result = load_schema(
        {'type': 'string', 'maxLength': 100, 'minLength': 1, 'readOnly': True},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result, Schema)
    assert result.type == OpenAPIType.STRING
    assert result.max_length == 100
    assert result.min_length == 1
    assert result.read_only is True


def test_load_schema_all_of_inline() -> None:
    """``allOf`` with inline schema objects loads nested Schema instances."""
    result = load_schema(
        {'allOf': [{'type': 'string'}, {'minLength': 1}]},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result, Schema)
    assert result.all_of is not None
    assert len(result.all_of) == 2
    first, second = result.all_of
    assert isinstance(first, Schema)
    assert first.type == OpenAPIType.STRING
    assert isinstance(second, Schema)
    assert second.min_length == 1


def test_load_schema_all_of_ref() -> None:
    """``allOf`` entry with ``$ref`` loads into a ``Reference`` instance."""
    result = load_schema(
        {'allOf': [{'$ref': '#/components/schemas/Base'}]},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result, Schema)
    assert result.all_of is not None
    ref = result.all_of[0]
    assert isinstance(ref, Reference)
    assert ref.ref == '#/components/schemas/Base'


def test_load_schema_all_of_mixed() -> None:
    """``allOf`` can mix ``$ref`` and inline schema entries."""
    result = load_schema(
        {
            'allOf': [
                {'$ref': '#/components/schemas/A'},
                {'type': 'object', 'description': 'extension'},
            ],
        },
        Schema,
        PydanticSerializer,
    )

    all_of = result.all_of
    assert all_of is not None
    assert isinstance(all_of[0], Reference)
    assert all_of[0].ref == '#/components/schemas/A'
    assert isinstance(all_of[1], Schema)
    assert all_of[1].type == OpenAPIType.OBJECT


def test_load_schema_any_of() -> None:
    """``anyOf`` with mixed entries loads correctly."""
    result = load_schema(
        {
            'anyOf': [
                {'$ref': '#/components/schemas/A'},
                {'type': 'string', 'minLength': 1},
            ],
        },
        Schema,
        PydanticSerializer,
    )

    any_of = result.any_of
    assert any_of is not None
    assert isinstance(any_of[0], Reference)
    assert any_of[0].ref == '#/components/schemas/A'
    assert isinstance(any_of[1], Schema)
    assert any_of[1].min_length == 1


def test_load_schema_properties_preserves_keys() -> None:
    """``properties`` dict keys (property names) are preserved as-is."""
    result = load_schema(
        {
            'type': 'object',
            'properties': {
                'myProp': {'type': 'string', 'maxLength': 50},
                'another_prop': {'type': 'integer', 'minimum': 0},
            },
        },
        Schema,
        PydanticSerializer,
    )

    assert result.properties is not None
    assert 'myProp' in result.properties
    assert 'another_prop' in result.properties
    assert result.properties['myProp'].max_length == 50
    assert result.properties['another_prop'].type == OpenAPIType.INTEGER


def test_load_schema_properties_with_ref() -> None:
    """``properties`` values can be ``$ref`` objects."""
    result = load_schema(
        {
            'type': 'object',
            'properties': {
                'owner': {'$ref': '#/components/schemas/User'},
            },
        },
        Schema,
        PydanticSerializer,
    )

    assert result.properties is not None
    owner = result.properties['owner']
    assert isinstance(owner, Reference)
    assert owner.ref == '#/components/schemas/User'


def test_load_schema_defs_preserves_keys() -> None:
    """``$defs`` dict keys (definition names) are preserved as-is."""
    result = load_schema(
        {
            '$defs': {
                'MyType': {'type': 'string'},
                'AnotherType': {'type': 'integer'},
            },
            'allOf': [{'$ref': '#/$defs/MyType'}],
        },
        Schema,
        PydanticSerializer,
    )

    assert result.defs is not None
    assert 'MyType' in result.defs
    assert 'AnotherType' in result.defs
    assert result.defs['MyType'].type == OpenAPIType.STRING
    assert result.defs['AnotherType'].type == OpenAPIType.INTEGER
    assert result.all_of is not None
    assert isinstance(result.all_of[0], Reference)


def test_load_schema_not_keyword() -> None:
    """The ``not`` keyword (alias for ``schema_not``) loads correctly."""
    result = load_schema(
        {'not': {'type': 'string'}},
        Schema,
        PydanticSerializer,
    )

    assert result.schema_not is not None
    assert isinstance(result.schema_not, Schema)
    assert result.schema_not.type == OpenAPIType.STRING


def test_load_schema_not_with_ref() -> None:
    """The ``not`` keyword can reference a ``$ref`` object."""
    result = load_schema(
        {'not': {'$ref': '#/components/schemas/Forbidden'}},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result.schema_not, Reference)
    assert result.schema_not.ref == '#/components/schemas/Forbidden'


def test_load_schema_dynamic_ref() -> None:
    """``$dynamicRef`` loads into ``Schema.dynamic_ref``."""
    result = load_schema(
        {'$dynamicRef': '#T'},
        Schema,
        PydanticSerializer,
    )

    assert result.dynamic_ref == '#T'


def test_load_schema_dynamic_anchor() -> None:
    """``$dynamicAnchor`` loads into ``Schema.dynamic_anchor``."""
    result = load_schema(
        {'$dynamicAnchor': 'T'},
        Schema,
        PydanticSerializer,
    )

    assert result.dynamic_anchor == 'T'


def test_load_schema_generic_list_pattern() -> None:
    """A generic List<T> schema with ``$defs``, ``$dynamicAnchor``, and ``$dynamicRef``."""
    result = load_schema(
        {
            'type': 'array',
            '$defs': {'content': {'$dynamicAnchor': 'T'}},
            'items': {'$dynamicRef': '#T'},
        },
        Schema,
        PydanticSerializer,
    )

    assert result.type == OpenAPIType.ARRAY
    assert result.defs is not None
    assert 'content' in result.defs
    assert result.defs['content'].dynamic_anchor == 'T'
    assert isinstance(result.items, Schema)
    assert result.items.dynamic_ref == '#T'


def test_load_schema_additional_properties_bool() -> None:
    """``additionalProperties`` set to a boolean loads correctly."""
    result = load_schema(
        {'type': 'object', 'additionalProperties': False},
        Schema,
        PydanticSerializer,
    )

    assert result.additional_properties is False


def test_load_schema_additional_properties_schema() -> None:
    """``additionalProperties`` as an inline schema loads into Schema."""
    result = load_schema(
        {'type': 'object', 'additionalProperties': {'type': 'string'}},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result.additional_properties, Schema)
    assert result.additional_properties.type == OpenAPIType.STRING


def test_load_schema_additional_properties_ref() -> None:
    """``additionalProperties`` as a ``$ref`` loads into a Reference."""
    result = load_schema(
        {'type': 'object', 'additionalProperties': {'$ref': '#/components/schemas/Value'}},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result.additional_properties, Reference)
    assert result.additional_properties.ref == '#/components/schemas/Value'


def test_load_schema_items_inline() -> None:
    """``items`` as an inline schema loads into Schema."""
    result = load_schema(
        {'type': 'array', 'items': {'type': 'string', 'maxLength': 100}},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result.items, Schema)
    assert result.items.type == OpenAPIType.STRING
    assert result.items.max_length == 100


def test_load_schema_items_ref() -> None:
    """``items`` as a ``$ref`` loads into a Reference."""
    result = load_schema(
        {'type': 'array', 'items': {'$ref': '#/components/schemas/Item'}},
        Schema,
        PydanticSerializer,
    )

    assert isinstance(result.items, Reference)
    assert result.items.ref == '#/components/schemas/Item'


def test_load_schema_nested_properties() -> None:
    """Deeply nested ``properties`` (object within object) load correctly.

    Note: property name keys inside *nested* schema values go through
    ``_normalize_nested_dict``, which converts camelCase to snake_case.
    Only top-level dict fields use ``_is_dict_field`` to preserve keys.
    Use plain lowercase property names to avoid unintended conversion.
    """
    result = load_schema(
        {
            'type': 'object',
            'properties': {
                'address': {
                    'type': 'object',
                    'properties': {
                        'street': {'type': 'string'},
                        'zip': {'type': 'string', 'maxLength': 10},
                    },
                },
            },
        },
        Schema,
        PydanticSerializer,
    )

    assert result.properties is not None
    address = result.properties['address']
    assert isinstance(address, Schema)
    assert address.properties is not None
    assert 'street' in address.properties
    assert 'zip' in address.properties
    assert address.properties['zip'].max_length == 10


# ==============================================================================
# load_schema — PathItem
# ==============================================================================


def test_load_path_item_ref() -> None:
    """``PathItem`` with ``$ref`` loads into ``PathItem.ref``."""
    result = load_schema(
        {'$ref': 'https://other-api.com/openapi.yaml#/paths/~1users'},
        PathItem,
        PydanticSerializer,
    )

    assert isinstance(result, PathItem)
    assert result.ref == 'https://other-api.com/openapi.yaml#/paths/~1users'


def test_load_path_item_get_operation() -> None:
    """``PathItem.get`` with a full Operation loads nested fields."""
    result = load_schema(
        {
            'get': {
                'summary': 'List users',
                'operationId': 'listUsers',
                'deprecated': False,
                'tags': ['users'],
            },
        },
        PathItem,
        PydanticSerializer,
    )

    assert result.get is not None
    assert result.get.summary == 'List users'
    assert result.get.operation_id == 'listUsers'
    assert result.get.deprecated is False
    assert result.get.tags == ['users']


def test_load_path_item_multiple_methods() -> None:
    """``PathItem`` with multiple HTTP methods loads each operation."""
    result = load_schema(
        {
            'get': {'summary': 'Get item', 'operationId': 'getItem'},
            'post': {'summary': 'Create item', 'operationId': 'createItem'},
            'delete': {'summary': 'Delete item', 'operationId': 'deleteItem'},
        },
        PathItem,
        PydanticSerializer,
    )

    assert result.get is not None
    assert result.get.operation_id == 'getItem'
    assert result.post is not None
    assert result.post.operation_id == 'createItem'
    assert result.delete is not None
    assert result.delete.operation_id == 'deleteItem'


def test_load_path_item_summary_and_ref() -> None:
    """``PathItem`` can have both ``$ref`` and ``summary``."""
    result = load_schema(
        {
            '$ref': './common-paths.yaml#/pets',
            'summary': 'Override summary',
            'description': 'Override description',
        },
        PathItem,
        PydanticSerializer,
    )

    assert result.ref == './common-paths.yaml#/pets'
    assert result.summary == 'Override summary'
    assert result.description == 'Override description'


# ==============================================================================
# load_schema — Reference
# ==============================================================================


def test_load_reference() -> None:
    """A ``$ref`` object loads into a ``Reference`` instance."""
    result = load_schema(
        {'$ref': '#/components/schemas/MyModel'},
        Reference,
        PydanticSerializer,
    )

    assert isinstance(result, Reference)
    assert result.ref == '#/components/schemas/MyModel'


def test_load_reference_with_summary() -> None:
    """A ``$ref`` with optional ``summary`` and ``description`` loads them."""
    result = load_schema(
        {
            '$ref': '#/components/schemas/MyModel',
            'summary': 'My model summary',
            'description': 'Detailed description',
        },
        Reference,
        PydanticSerializer,
    )

    assert result.ref == '#/components/schemas/MyModel'
    assert result.summary == 'My model summary'
    assert result.description == 'Detailed description'


# ==============================================================================
# round-trip: dump_schema → load_schema
# ==============================================================================


def test_round_trip_simple_schema() -> None:
    """Dumping and re-loading a simple Schema produces an equivalent object."""
    from dmr.openapi.mappers.schema_normalization import dump_schema  # noqa: PLC0415

    original = Schema(
        type=OpenAPIType.STRING,
        max_length=100,
        min_length=1,
        read_only=True,
        description='A string field',
    )

    dumped = dump_schema(original)
    restored = load_schema(dumped, Schema, PydanticSerializer)

    assert restored.type == original.type
    assert restored.max_length == original.max_length
    assert restored.min_length == original.min_length
    assert restored.read_only == original.read_only
    assert restored.description == original.description


def test_round_trip_schema_with_all_of() -> None:
    """Round-trip for Schema with ``allOf`` containing a Reference."""
    from dmr.openapi.mappers.schema_normalization import dump_schema  # noqa: PLC0415

    original = Schema(
        all_of=[Reference(ref='#/components/schemas/Base')],
        description='Extended schema',
    )

    dumped = dump_schema(original)
    restored = load_schema(dumped, Schema, PydanticSerializer)

    assert restored.all_of is not None
    assert len(restored.all_of) == 1
    assert isinstance(restored.all_of[0], Reference)
    assert restored.all_of[0].ref == '#/components/schemas/Base'


def test_round_trip_schema_with_defs() -> None:
    """Round-trip for Schema with ``$defs`` and ``$dynamicRef``."""
    from dmr.openapi.mappers.schema_normalization import dump_schema  # noqa: PLC0415

    original = Schema(
        type=OpenAPIType.ARRAY,
        defs={'content': Schema(dynamic_anchor='T')},
        items=Schema(dynamic_ref='#T'),
    )

    dumped = dump_schema(original)
    restored = load_schema(dumped, Schema, PydanticSerializer)

    assert restored.type == OpenAPIType.ARRAY
    assert restored.defs is not None
    assert 'content' in restored.defs
    assert restored.defs['content'].dynamic_anchor == 'T'
    assert isinstance(restored.items, Schema)
    assert restored.items.dynamic_ref == '#T'


@pytest.mark.parametrize(
    ('raw', 'expected_type', 'expected_ref'),
    [
        (
            {'$ref': '#/components/schemas/User'},
            Reference,
            '#/components/schemas/User',
        ),
        (
            {'type': 'string'},
            Schema,
            None,
        ),
    ],
)
def test_load_schema_ref_vs_inline(
    *,
    raw: dict[str, Any],
    expected_type: type,
    expected_ref: str | None,
) -> None:
    """A dict with ``$ref`` loads as Reference; without as Schema."""
    result = load_schema(raw, expected_type, PydanticSerializer)
    assert isinstance(result, expected_type)
    if expected_ref is not None:
        assert result.ref == expected_ref  # type: ignore[union-attr]
