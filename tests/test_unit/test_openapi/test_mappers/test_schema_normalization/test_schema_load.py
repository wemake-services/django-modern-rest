import json
from collections.abc import Callable

import yaml
from syrupy.assertion import SnapshotAssertion

from dmr.openapi import load_schema
from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.openapi import OpenAPI


def test_load_schema(
    snapshot: SnapshotAssertion,
    named_text_fixture: Callable[[str], str],
) -> None:
    """Ensure that ``dump_field`` converts field names to OpenAPI keys."""
    schema = yaml.safe_load(named_text_fixture('django-allauth.yml'))

    loaded = load_schema(schema, OpenAPI)

    assert isinstance(loaded, OpenAPI)
    assert json.dumps(dump_schema(loaded), indent=2) == snapshot
