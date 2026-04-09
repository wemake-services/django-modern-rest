import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

from django.core.serializers.json import DjangoJSONEncoder
from typing_extensions import override

if TYPE_CHECKING:
    from dmr.openapi.objects.openapi import ConvertedSchema
    from dmr.openapi.views.base import DumpedSchema, SchemaDumper
    from dmr.parsers import Raw


class JsonModule(Protocol):
    """
    Json module protocol.

    This is how we use our json modules to parse / render data.
    """

    def dumps(
        self,
        to_serialize: Any,
        /,
        default: Callable[[Any], Any] | None = None,
    ) -> bytes:
        """How data should be serialized."""
        raise NotImplementedError

    def loads(self, to_deserialize: Any, /) -> Any:
        """How data should be deserialized."""
        raise NotImplementedError


class _DMREncoder(DjangoJSONEncoder):
    def __init__(
        self,
        *args: Any,
        serializer_hook: Callable[[Any], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._serializer_hook = serializer_hook

    @override
    def default(self, o: Any) -> Any:  # noqa: WPS111
        try:
            return super().default(o)
        except TypeError:
            if self._serializer_hook:
                return self._serializer_hook(o)
            raise


class NativeJson:
    """Native json module implementation."""

    @classmethod
    def dumps(
        cls,
        to_serialize: Any,
        /,
        default: Callable[[Any], Any] | None = None,
    ) -> bytes:
        """Internal method to dump json to bytes."""
        return json.dumps(
            to_serialize,
            serializer_hook=default,
            cls=_DMREncoder,
            # We need this flag to produce the same results as `msgspec`:
            separators=(',', ':'),
        ).encode('utf8')

    @classmethod
    def loads(cls, to_deserialize: 'Raw', /) -> Any:
        """Internal method to load json as a simple object."""
        return json.loads(to_deserialize)


# Schema dumps
# ------------


def _wrap_bytes_dumper(
    dumper: Callable[['ConvertedSchema'], bytes],
) -> 'SchemaDumper':
    """
    Wrap a bytes-returning JSON dumper to always return a UTF-8 string.

    This is used to normalize different JSON backends (e.g. `msgspec`)
    to a single `str`-based interface expected by `json_dump_schema`.
    """

    def wrapper(schema: 'ConvertedSchema') -> 'DumpedSchema':
        return dumper(schema).decode('utf-8')

    return wrapper


try:
    import msgspec
except ImportError:  # pragma: no cover
    _json_dumps: 'SchemaDumper' = json.dumps
else:
    _json_dumps = _wrap_bytes_dumper(msgspec.json.encode)


def json_dump_schema(schema: 'ConvertedSchema') -> 'DumpedSchema':
    """
    Serialize `ConvertedSchema` to a decoded JSON string.

    Args:
        schema: Converted OpenAPI schema to be serialized.

    Returns:
        JSON string representation of the schema.

    """
    return _json_dumps(schema)
