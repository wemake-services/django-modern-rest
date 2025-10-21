# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/serialization/msgspec_hooks.py
# under MIT license.

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import msgspec

from django_modern_rest.exceptions import DataParsingError

if TYPE_CHECKING:
    from django_modern_rest.internal.json import (
        DeserializeFunc,
        FromJson,
    )


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
    return msgspec.json.encode(
        to_serialize,
        enc_hook=serializer,
    )


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

    Returns:
        Decoded object.

    Raises:
        DataParsingError: If error encoding ``obj``.

    """
    try:
        return msgspec.json.decode(
            to_deserialize,
            dec_hook=deserializer,
            strict=strict,
        )
    except msgspec.DecodeError as exc:
        raise DataParsingError(str(exc)) from exc
