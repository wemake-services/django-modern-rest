# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/serialization/msgspec_hooks.py
# under MIT license.

from collections.abc import Callable
from typing import Any, Protocol, TypeAlias

import msgspec

#: Types that are possible to load json from.
FromJson: TypeAlias = str | bytes | bytearray

#: Type that represents the `serialize` callback.
Serialize: TypeAlias = Callable[[Any, Callable[[Any], Any]], bytes]

_DeserializeFunc: TypeAlias = Callable[[type[Any], Any], Any]


class Deserialize(Protocol):
    """Type that represents the `deserialize` callback."""

    def __call__(
        self,
        to_deserialize: FromJson,
        deserializer: _DeserializeFunc,
        *,
        strict: bool = ...,
    ) -> Any: ...


def serialize(
    to_serialize: Any,
    serializer: Callable[[Any], Any] | None = None,
) -> bytes:
    """
    Encode a value into JSON bytestring.

    Args:
        to_serialize: Value to encode.
        serializer: Optional callable to support non-natively supported types.

    Returns:
        JSON as bytes.

    Raises:
        TypeError: If error encoding ``obj``.
        msgspec.EncodeError: If error encoding ``obj``.
    """
    return msgspec.json.encode(to_serialize, enc_hook=serializer)


def deserialize(
    to_deserialize: FromJson,
    deserializer: _DeserializeFunc | None = None,
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
        TypeError: If error encoding ``obj``.
        msgspec.DecodeError: If error encoding ``obj``.
    """
    return msgspec.json.decode(
        to_deserialize,
        dec_hook=deserializer,
        strict=strict,
    )
