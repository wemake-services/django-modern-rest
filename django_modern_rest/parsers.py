import abc
import json
from collections.abc import Callable
from typing import Any, ClassVar, TypeAlias

from typing_extensions import override

from django_modern_rest.exceptions import DataParsingError

#: Types that are possible to load json from.
Raw: TypeAlias = str | bytes | bytearray


#: Type that represents the `deserializer` hook.
DeserializeFunc: TypeAlias = Callable[[type[Any], Any], Any]


class Parser:
    """
    Base class for all parsers.

    Subclass it to implement your own parsers.
    """

    __slots__ = ()

    # Must be defined in all subclasses:
    content_type: ClassVar[str]

    @classmethod
    @abc.abstractmethod
    def parse(
        cls,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
        *,
        strict: bool = True,
    ) -> Any:
        """
        Deserialize a raw string/bytes/bytearray into an object.

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


class JsonParser(Parser):
    """
    Fallback implementation of a json parser.

    Only is used when ``msgspec`` is not installed.

    .. warning::

        It is not recommended to be used directly.
        It is slow and has less features.

    """

    __slots__ = ()

    content_type: ClassVar[str] = 'application/json'

    @override
    @classmethod
    def parse(
        cls,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
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
            if to_deserialize == b'':
                return None
            raise DataParsingError(str(exc)) from exc
