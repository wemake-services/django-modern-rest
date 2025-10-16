import pytest

from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.response import build_response


def test_build_response_no_status() -> None:
    """Ensure that either method name or status_code is required."""
    with pytest.raises(ValueError, match='status_code'):
        build_response(None, PydanticSerializer, raw_data=[])  # type: ignore[call-overload]
