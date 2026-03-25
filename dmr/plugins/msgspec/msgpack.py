from collections.abc import Callable
from functools import lru_cache
from typing import Any, ClassVar

import msgspec
from django.http import HttpRequest
from typing_extensions import override

from dmr.envs import MAX_CACHE_SIZE
from dmr.exceptions import DataParsingError
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.renderers import Renderer


class MsgpackParser(Parser):
    """Parsers ``msgpack`` bodies using ``msgspec``."""

    content_type = 'application/msgpack'
    strict: ClassVar[bool] = True

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """
        Deserialize a raw msgpack string/bytes/bytearray into an object.

        Args:
            to_deserialize: Value to deserialize.
            deserializer_hook: Hook to convert types
                that are not natively supported.
            request: Django's original request with all the details.
            model: Model that reprensents the final result's structure.

        Returns:
            Simple python object with primitive parts.

        Raises:
            DataParsingError: If error decoding ``obj``.

        """
        try:
            return _get_deserializer(
                deserializer_hook,
                strict=self.strict,
            ).decode(to_deserialize)
        except msgspec.DecodeError as exc:
            # Corner case: when deserializing an empty body,
            # return `None` instead.
            # We do this here, because we don't want
            # a penalty for all positive cases.
            if to_deserialize == b'':
                return None
            raise DataParsingError(str(exc)) from exc


class MsgpackRenderer(Renderer):
    """Renders ``msgpack`` bodies using ``msgspec``."""

    content_type = 'application/msgpack'

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Callable[[Any], Any] | None = None,
    ) -> bytes:
        """
        Encode a value into ``msgpack`` bytestring.

        Args:
            to_serialize: Value to encode.
            serializer_hook: Callable to support non-natively supported types.

        Returns:
            ``msgpack`` as bytes.
        """
        return _get_serializer(serializer_hook).encode(to_serialize)

    @property
    @override
    def validation_parser(self) -> MsgpackParser:
        """Msgspec can parse this."""
        return MsgpackParser()


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_serializer(
    serializer_hook: Callable[[Any], Any] | None,
) -> msgspec.msgpack.Encoder:
    """
    Returns cached serializer.

    If you want to clear this cache run:

    .. code:: python

        >>> _get_serializer.cache_clear()

    """
    return msgspec.msgpack.Encoder(enc_hook=serializer_hook)


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_deserializer(
    deserializer_hook: DeserializeFunc | None,
    *,
    strict: bool,
) -> msgspec.msgpack.Decoder[Any]:
    """
    Returns cached deserializer.

    If you want to clear this cache run:

    .. code:: python

        >>> _get_deserializer.cache_clear()

    """
    return msgspec.msgpack.Decoder(dec_hook=deserializer_hook, strict=strict)
