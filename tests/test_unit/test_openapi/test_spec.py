import pytest
from django.conf import LazySettings

from dmr.openapi import build_schema
from dmr.routing import Router


def test_config_raises_wrong_type(
    dmr_clean_settings: None,
    settings: LazySettings,
) -> None:
    """Ensure that ``TypeError`` raised with wrong config type."""
    settings.DMR_SETTINGS = {'openapi_config': 'not-an-object'}

    with pytest.raises(
        TypeError,
        match='OpenAPI config is not set',
    ):
        build_schema(router=Router([], prefix=''))
