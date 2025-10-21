from collections.abc import Callable
from typing import Any, Protocol, TypeAlias

try:  # noqa: WPS229
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

#: Type that represents the `serialize` callback.
Serialize: TypeAlias = Callable[[Any, Callable[[Any], Any]], bytes]

#: Type that represents the `deserializer` hook.
DeserializeFunc: TypeAlias = Callable[[type[Any], Any], Any]


class Deserialize(Protocol):
    """Type that represents the `deserialize` callback."""

    def __call__(
        self,
        to_deserialize: FromJson,
        deserializer: DeserializeFunc,
        *,
        strict: bool = ...,
    ) -> Any:
        """Function to be called on deserialization."""
