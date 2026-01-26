from collections.abc import Mapping
from typing import Any

import pytest

from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.negotiation import ContentType, content_negotiation


@pytest.mark.parametrize(
    'mapping',
    [
        {},
        {ContentType.json: str},
    ],
)
def test_wrong_content_negotiation(mapping: Mapping[ContentType, Any]) -> None:
    """Ensure that content_negotiation require >=2 types."""
    with pytest.raises(EndpointMetadataError, match='>= 2'):
        content_negotiation(mapping)
