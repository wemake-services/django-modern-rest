import pytest

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


@pytest.mark.parametrize('deprecated_value', [True, False])
def test_node_type_conflicts_with_attribute(*, deprecated_value: bool) -> None:
    """Ensure that `node_type` cannot be mixed with `attribute`."""
    with pytest.raises(ValueError, match='Both `node_type` and `attribute`'):
        XML(node_type='element', attribute=deprecated_value)


@pytest.mark.parametrize('deprecated_value', [True, False])
def test_node_type_conflicts_with_wrapped(*, deprecated_value: bool) -> None:
    """Ensure that `node_type` cannot be mixed with `wrapped`."""
    with pytest.raises(ValueError, match='Both `node_type` and `attribute`'):
        XML(node_type='element', wrapped=deprecated_value)
