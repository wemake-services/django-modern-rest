import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.core.serializers.json import DjangoJSONEncoder

from django_modern_rest.exceptions import DataParsingError

if TYPE_CHECKING:
    from django_modern_rest.internal.json import (
        DeserializeFunc,
        FromJson,
    )


class _DMREncoder(DjangoJSONEncoder):
    def __init__(
        self,
        *args: Any,
        serializer: Callable[[Any], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._serializer = serializer

    def default(self, o: Any) -> Any:
        try:
            return super().default(o)
        except TypeError:
            if self._serializer:
                return self._serializer(o)
            raise


def serialize(
    to_serialize: Any,
    serializer: Callable[[Any], Any] | None = None,
) -> bytes:
    """
    Encode a value into JSON bytestring.

    Args:
        to_serialize: Value to encode.
        serializer: Callable to support non-natively supported types.

    Returns:
        JSON as bytes.
    """
    # msgspec returns `bytes`, we prefer to use `bytes` by default
    # and not to create extra strings when not needed in "fast" mode.
    # We don't really care about raw json implementation. It is a fallback.
    return json.dumps(
        to_serialize,
        cls=_DMREncoder,
        serializer=serializer,
    ).encode('utf8')


def deserialize(
    to_deserialize: 'FromJson',
    deserializer: 'DeserializeFunc | None' = None,
    *,
    strict: bool = True,
) -> Any:
    """
    Decode a JSON string/bytes/bytearray into an object.

    Args:
        to_deserialize: Value to decode.
        deserializer: Hook to convert types that are not natively supported.
        strict: Whether type coercion rules should be strict.
            Setting to ``False`` enables a wider set of coercion rules
            from string to non-string types for all values.

    Raises:
        DataParsingError: If error decoding ``obj``.

    Returns:
        Decoded object.

    """
    try:
        return json.loads(
            to_deserialize,
            strict=strict,
            # TODO: support `deserializer`
        )
    except (ValueError, TypeError) as exc:
        raise DataParsingError(str(exc)) from exc
