from collections.abc import Mapping
from typing import Any

import pytest

from dmr.exceptions import EndpointMetadataError
from dmr.negotiation import ContentType, conditional_type


@pytest.mark.parametrize(
    'mapping',
    [
        {},
        {ContentType.json: str},
    ],
)
def test_wrong_conditional_type(mapping: Mapping[ContentType, Any]) -> None:
    """Ensure that conditional_type require >=2 types."""
    with pytest.raises(EndpointMetadataError, match='>= 2'):
        conditional_type(mapping)
