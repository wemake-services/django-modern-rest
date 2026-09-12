from decimal import Decimal
from typing import Any

from typing_extensions import override

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator


class MyMsgspecSchemaGenerator(MsgspecSchemaGenerator):
    """Plugs a custom `schema_hook` into msgspec schema generation."""

    __slots__ = ()

    @override
    @classmethod
    def schema_hook(cls, source_type: type) -> dict[str, Any]:
        """Teach msgspec how to build a schema for extra types."""
        if source_type is Decimal:
            return {'type': 'string', 'format': 'decimal'}
        raise NotImplementedError(f'Unsupported type: {source_type!r}')


class MySerializer(MsgspecSerializer):
    """Serializer using the customized schema generator."""

    __slots__ = ()

    schema_generator = MyMsgspecSchemaGenerator
