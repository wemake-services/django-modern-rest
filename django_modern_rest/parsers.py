import abc
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

from typing_extensions import override

from django_modern_rest.exceptions import (
    DataParsingError,
)
from django_modern_rest.metadata import ResponseSpec, ResponseSpecProvider

if TYPE_CHECKING:
    from django_modern_rest.serializer import BaseSerializer

#: Types that are possible to load json from.
Raw: TypeAlias = str | bytes | bytearray


#: Type that represents the `deserializer` hook.
DeserializeFunc: TypeAlias = Callable[[type[Any], Any], Any]


class Parser(ResponseSpecProvider):
    """
    Base class for all parsers.

    Subclass it to implement your own parsers.
    """

    __slots__ = ()

    content_type: ClassVar[str]
    """
    Content-Type that this parser works with.

    Must be defined for all subclasses.
    """

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

    @override
    @classmethod
    def provide_response_specs(
        cls,
        serializer: type['BaseSerializer'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when data can't be parsed."""
        # We don't provide parser errors by default, because parser only works
        # when there are active components. But, components already provide
        # required response specs. This method is only useful
        # for custom user-defined errors.
        return []


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
    """Works with ``json`` only."""

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
            return json.loads(to_deserialize, strict=strict)
        except (ValueError, TypeError) as exc:
            if to_deserialize == b'':
                return None
            raise DataParsingError(str(exc)) from exc
