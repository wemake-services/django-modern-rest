from collections.abc import Callable
from functools import lru_cache
from typing import Any, ClassVar

import msgspec
from typing_extensions import override

from django_modern_rest.envs import MAX_CACHE_SIZE
from django_modern_rest.exceptions import DataParsingError
from django_modern_rest.parsers import DeserializeFunc, Parser, Raw
from django_modern_rest.renderers import Renderer


class MsgspecJsonParser(Parser):
    """Parsers json bodies using ``msgspec``."""

    content_type: ClassVar[str] = 'application/json'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
        *,
        strict: bool = True,
    ) -> Any:
        """
        Deserialize a raw JSON string/bytes/bytearray into an object.

        Args:
            to_deserialize: Value to deserialize.
            deserializer: Hook to convert types that are not natively supported.
            strict: Whether type coercion rules should be strict.
                Setting to ``False`` enables a wider set of coercion rules
                from string to non-string types for all values.

        Raises:
            DataParsingError: If error decoding ``obj``.

        Returns:
            Simple python object with primitive parts.

        """
        try:
            return _get_deserializer(
                deserializer,
                strict=strict,
            ).decode(to_deserialize)
        except msgspec.DecodeError as exc:
            # Corner case: when deserializing an empty body,
            # return `None` instead.
            # We do this here, because we don't want
            # a penalty for all positive cases.
            if to_deserialize == b'':
                return None
            raise DataParsingError(str(exc)) from exc


class MsgspecJsonRenderer(Renderer):
    """Renders json bodies using ``msgspec``."""

    content_type: ClassVar[str] = 'application/json'

    @override
    def render(
        self,
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


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_serializer(
    serializer: Callable[[Any], Any] | None,
) -> msgspec.json.Encoder:
    return msgspec.json.Encoder(enc_hook=serializer)


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_deserializer(
    deserializer: DeserializeFunc | None,
    *,
    strict: bool,
) -> msgspec.json.Decoder[Any]:
    return msgspec.json.Decoder(dec_hook=deserializer, strict=strict)
