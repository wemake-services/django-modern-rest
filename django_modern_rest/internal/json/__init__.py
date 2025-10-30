from collections.abc import Callable
from typing import Any, Protocol, TypeAlias

try:  # noqa: WPS229  # pragma: no cover
    from django_modern_rest.internal.json.msgspec import (
        deserialize as deserialize,
    )
    from django_modern_rest.internal.json.msgspec import serialize as serialize
except ImportError:  # pragma: no cover
    from django_modern_rest.internal.json.raw import (
        deserialize as deserialize,
    )
    from django_modern_rest.internal.json.raw import (
        serialize as serialize,
    )

#: Types that are possible to load json from.
FromJson: TypeAlias = str | bytes | bytearray


class Serialize(Protocol):
    """Type that represents the `serialize` callback."""

    def __call__(
        self,
        to_serialize: Any,
        serializer: Callable[[Any], Any],
    ) -> bytes:  # pyright: ignore[reportReturnType]
        """Function to be called on object serialization."""


#: Type that represents the `deserializer` hook.
DeserializeFunc: TypeAlias = Callable[[type[Any], Any], Any]


class Deserialize(Protocol):
    """Type that represents the `deserialize` callback."""

    def __call__(
        self,
        to_deserialize: FromJson,
        deserializer: DeserializeFunc,
        *,
        strict: bool = True,
    ) -> Any:
        """Function to be called on object deserialization."""
