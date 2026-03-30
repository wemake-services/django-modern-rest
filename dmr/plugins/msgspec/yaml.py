from typing import TYPE_CHECKING

import msgspec

if TYPE_CHECKING:
    from dmr.openapi.objects.openapi import ConvertedSchema
    from dmr.openapi.views.base import DumpedSchema


def yaml_dumps(schema: 'ConvertedSchema') -> 'DumpedSchema':
    """Serialize schema to a decoded YAML string."""
    return msgspec.yaml.encode(schema).decode('utf-8')
