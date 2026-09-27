from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.objects import XML


def test_empty_xml_is_dumped_as_empty() -> None:
    """Ensure that deprecated `attribute` and `wrapped` are not dumped."""
    assert dump_schema(XML()) == {}


def test_xml_node_type() -> None:
    """Ensure that the 3.2 `node_type` replaces `attribute` and `wrapped`."""
    assert dump_schema(XML(name='pet', node_type='attribute')) == {
        'name': 'pet',
        'nodeType': 'attribute',
    }


def test_deprecated_xml_fields_are_still_dumped() -> None:
    """Ensure that explicit `attribute` and `wrapped` still work."""
    assert dump_schema(XML(attribute=True, wrapped=False)) == {
        'attribute': True,
        'wrapped': False,
    }
