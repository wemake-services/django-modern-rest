# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/serialization/msgspec_hooks.py
# under MIT license.

from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import msgspec

from django_modern_rest.exceptions import DataParsingError
from django_modern_rest.settings import MAX_CACHE_SIZE

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
    return _get_serializer(serializer).encode(to_serialize)


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
        return _get_deserializer(
            deserializer,
            strict=strict,
        ).decode(to_deserialize)
    except msgspec.DecodeError as exc:
        # Corner case: when deserializing an empty body, return `null` instead.
        # We do this here, because we don't want
        # a penalty for all posiive cases.
        if to_deserialize == b'':
            return None
        raise DataParsingError(str(exc)) from exc


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_serializer(
    serializer: Callable[[Any], Any] | None,
) -> msgspec.json.Encoder:
    return msgspec.json.Encoder(enc_hook=serializer)


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_deserializer(
    deserializer: 'DeserializeFunc | None',
    *,
    strict: bool,
) -> msgspec.json.Decoder[Any]:
    return msgspec.json.Decoder(dec_hook=deserializer, strict=strict)
