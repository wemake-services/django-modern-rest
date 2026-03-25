import pytest

from dmr.openapi.objects import Encoding, MediaType, OpenAPIType, Schema


def test_media_type_validation() -> None:
    """Ensure that MediaType can't be created with invalid fields."""
    with pytest.raises(ValueError, match='Both `schema` and `item_schema`'):
        MediaType()

    encoding = {'text/plain': Encoding()}
    schema = Schema(type=OpenAPIType.OBJECT)
    with pytest.raises(ValueError, match='Both `encoding` and `item_encoding`'):
        MediaType(schema=schema, encoding=encoding, item_encoding=Encoding())
    with pytest.raises(ValueError, match='Both `encoding` and `item_encoding`'):
        MediaType(schema=schema, encoding=encoding, prefix_encoding=Encoding())
