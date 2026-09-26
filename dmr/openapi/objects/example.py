from dataclasses import dataclass
from typing import Any

from dmr.internal.empty import EMPTY


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
        ``value`` and ``data_value`` now default to
        :data:`~dmr.types.EMPTY` instead of ``None``,
        because ``None`` is a valid value for them.

    """

    summary: str | None = None
    description: str | None = None
    value: Any = EMPTY
    external_value: str | None = None

    # OpenAPI 3.2+ fields:
    # NOTE: deprecated `value` excludes all three fields below,
    # and `serialized_value` excludes `external_value`,
    # we let `openapi-spec-validator` report that.
    #: Example of the data structure, it must validate against the schema.
    data_value: Any = EMPTY
    #: Example of the serialized form, as the media type requires it.
    serialized_value: str | None = None
