from dataclasses import dataclass
from typing import Any


@dataclass(kw_only=True, slots=True)
class Example:
    """
    Example Object.

    In all cases, the example value is expected to be compatible with the
    type schema of its associated value. Tooling implementations MAY choose
    to validate compatibility automatically, and reject the example
    value(s) if incompatible.

    .. versionchanged:: 0.16.0
        Added ``data_value`` and ``serialized_value`` from OpenAPI 3.2.
        They replace ``value``, which 3.2 deprecates
        for non-JSON serialization targets.

    """

    summary: str | None = None
    description: str | None = None
    value: Any | None = None
    external_value: str | None = None

    # OpenAPI 3.2+ fields:
    #: Example of the data structure, it must validate against the schema.
    data_value: Any | None = None
    #: Example of the serialized form, as the media type requires it.
    serialized_value: str | None = None

    def __post_init__(self) -> None:
        """Validate the object."""
        if self.value is not None and (
            self.data_value is not None
            or self.serialized_value is not None
            or self.external_value is not None
        ):
            raise ValueError(
                'Both `value` and `data_value`, `serialized_value`, '
                'or `external_value` cannot be set',
            )
        if self.serialized_value is not None and (
            self.external_value is not None
        ):
            raise ValueError(
                'Both `serialized_value` and `external_value` cannot be set',
            )
