# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/params.py
# under MIT license.
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from django_modern_rest.types import Empty, EmptyObj


@dataclass(frozen=True)
class KwargDefinition:
    """Data container representing a constrained kwarg."""

    # TODO: use type/dataclass for examples
    examples: list[dict[str, Any]] | None = field(default=None)
    # TODO: use type/dataclass for external docs
    external_docs: dict[str, Any] | None = field(default=None)
    content_encoding: str | None = field(default=None)
    default: Any = field(default=Empty)
    title: str | None = field(default=None)
    description: str | None = field(default=None)
    const: bool | None = field(default=None)
    gt: float | None = field(default=None)
    ge: float | None = field(default=None)
    lt: float | None = field(default=None)
    le: float | None = field(default=None)
    multiple_of: float | None = field(default=None)
    min_items: int | None = field(default=None)
    max_items: int | None = field(default=None)
    min_length: int | None = field(default=None)
    max_length: int | None = field(default=None)
    pattern: str | None = field(default=None)
    lower_case: bool | None = field(default=None)
    upper_case: bool | None = field(default=None)
    format: str | None = field(default=None)
    enum: Sequence[Any] | None = field(default=None)
    read_only: bool | None = field(default=None)
    schema_extra: dict[str, Any] | None = field(default=None)
    schema_component_key: str | None = None
    include_in_schema: bool = True


@dataclass(slots=True, frozen=True)
class FieldDefinition:
    """Definition of a field in the OpenAPI."""

    name: str
    default: Any | Empty = EmptyObj
    extra_data: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    kwarg_definition: KwargDefinition | None = field(default=None)
