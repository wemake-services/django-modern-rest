import pytest

from dmr.openapi.objects import MediaType


def test_media_type_validation() -> None:
    """Ensure that MediaType can't be created with invalid fields."""
    with pytest.raises(ValueError, match='Both `schema` and `item_schema`'):
        MediaType()
