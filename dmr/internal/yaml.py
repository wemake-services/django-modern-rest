from typing import TYPE_CHECKING

import msgspec

from dmr.internal.json import _wrap_bytes_dumper

if TYPE_CHECKING:
    from dmr.openapi.views.base import SchemaDumper


_yaml_dumps: 'SchemaDumper' = _wrap_bytes_dumper(msgspec.yaml.encode)


def yaml_dumps(schema: object) -> str:
    """Serialize schema to a decoded YAML string."""
    return _yaml_dumps(schema)
